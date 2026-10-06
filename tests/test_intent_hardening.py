"""Intent hardening: retry/backoff on transient LLM failures, and richer intent evidence.

Offline – the LLM HTTP calls are mocked with respx; no live network."""

import time

import httpx
import pytest
import respx

from gtm_engine.llm.client import GroqLLM, TokenBucket, _estimate_tokens, _post_with_retry
from gtm_engine.models import DiscoveredCompany, Signals
from gtm_engine.pipeline import _intent_evidence
from gtm_engine.qualification.buyer_classifier import TextBundle

URL = "https://x.test/chat"


# --- retry/backoff -----------------------------------------------------------------------

@respx.mock
async def test_retry_recovers_from_a_429():
    route = respx.post(URL).mock(side_effect=[
        httpx.Response(429, headers={"retry-after": "0"}),
        httpx.Response(200, json={"ok": True}),
    ])
    async with httpx.AsyncClient() as c:
        r = await _post_with_retry(c, URL, base_delay=0.0)
    assert r.status_code == 200 and route.call_count == 2


@respx.mock
async def test_retry_recovers_from_a_5xx():
    route = respx.post(URL).mock(side_effect=[httpx.Response(503), httpx.Response(200, json={})])
    async with httpx.AsyncClient() as c:
        r = await _post_with_retry(c, URL, base_delay=0.0)
    assert r.status_code == 200 and route.call_count == 2


@respx.mock
async def test_retry_gives_up_and_returns_the_last_response():
    respx.post(URL).mock(return_value=httpx.Response(503))
    async with httpx.AsyncClient() as c:
        r = await _post_with_retry(c, URL, retries=3, base_delay=0.0)
    assert r.status_code == 503


@respx.mock
async def test_plain_4xx_is_not_retried():
    route = respx.post(URL).mock(return_value=httpx.Response(400))
    async with httpx.AsyncClient() as c:
        r = await _post_with_retry(c, URL, base_delay=0.0)
    assert r.status_code == 400 and route.call_count == 1


@respx.mock
async def test_transient_network_error_is_retried_then_raises():
    route = respx.post(URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(httpx.ConnectError):
        async with httpx.AsyncClient() as c:
            await _post_with_retry(c, URL, retries=3, base_delay=0.0)
    assert route.call_count == 3


@respx.mock
async def test_groq_complete_retries_a_rate_limit_then_succeeds():
    respx.post("https://api.groq.com/openai/v1/chat/completions").mock(side_effect=[
        httpx.Response(429, headers={"retry-after": "0"}),
        httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]}),
    ])
    assert await GroqLLM("k").complete("s", "u") == "hi"


# --- proactive token pacing --------------------------------------------------------------

async def test_token_bucket_allows_calls_within_budget_without_waiting():
    bucket = TokenBucket(tokens_per_min=6000)   # starts full
    t0 = time.monotonic()
    await bucket.acquire(1000)
    await bucket.acquire(1000)
    assert time.monotonic() - t0 < 0.1


async def test_token_bucket_waits_once_the_budget_is_spent():
    bucket = TokenBucket(tokens_per_min=6000)   # 100 tokens/sec refill
    await bucket.acquire(6000)                   # drain it
    t0 = time.monotonic()
    await bucket.acquire(50)                      # ~0.5s to refill 50 at 100/sec
    assert time.monotonic() - t0 >= 0.4


def test_token_estimate_counts_prompt_and_output_ceiling():
    assert _estimate_tokens("a" * 400, "b" * 400, 300) == 200 + 300


# --- richer intent evidence --------------------------------------------------------------

def _bundle(**kw):
    kw.setdefault("title", None)
    kw.setdefault("about_text", None)
    return TextBundle(name=kw.pop("name", "Zed"), description=kw.pop("description", "desc"),
                      body_text=kw.pop("body_text", "text"), **kw)


def test_evidence_includes_observed_signals():
    company = DiscoveredCompany(name="Zed", source="osm", category="shop=clothes")
    signals = Signals(
        buying={"operations_scale": ["operates multiple branches/outlets"]},
        pain={"customer_service_load": ["takes orders over WhatsApp"]},
        technologies=["shopify"],
        job_openings=[{"title": "Inventory Planner", "growth_role": True}],
        intent=[{"kind": "hiring", "text": "hiring an inventory manager"}],
    )
    ev = _intent_evidence(company, _bundle(description="Apparel brand"), signals)
    assert "operates multiple branches/outlets" in ev
    assert "Technologies: shopify" in ev
    assert "Hiring: Inventory Planner" in ev
    assert "Intent signal (hiring)" in ev
    assert "Apparel brand" in ev


def test_evidence_without_signals_is_backwards_compatible():
    company = DiscoveredCompany(name="Zed", source="osm")
    ev = _intent_evidence(company, _bundle(description="desc", body_text="body"))
    assert "Zed" in ev and "desc" in ev and "body" in ev
