"""Slice 2 end-to-end: with the LLM on, the pipeline asks judge_intent per company and the
verdict lands on the lead and can flip the type. Reuses the acceptance-test mock world; the
LLM is faked (no network) and injected onto the pipeline."""

import json

import httpx
import respx

from conftest import fixture
from gtm_engine.discovery.geocode import NOMINATIM_URL
from gtm_engine.models import CompanyType
from gtm_engine.pipeline import Pipeline
from gtm_engine.scraping.fetcher import HttpFetcher
from gtm_engine.storage.database import Database


class FakeMX:
    async def has_mx(self, domain: str) -> bool:
        return domain in {"zarafabrics.pk", "pixeldigital.pk"}


class RoutingLLM:
    """Answers judge_intent with a fixed verdict; anything else (keyword generation) gets an
    empty list so the rest of the run is unaffected."""
    name = "fake"

    def __init__(self, verdict: dict):
        self._verdict = json.dumps(verdict)

    async def complete(self, system, user, *, max_tokens=400):
        if "Judge need" in user:
            return self._verdict
        return "[]"


def _html(body: str) -> httpx.Response:
    return httpx.Response(200, text=body, headers={"content-type": "text/html; charset=utf-8"})


def _mock_world(settings):
    respx.get(url__startswith=NOMINATIM_URL).mock(
        return_value=httpx.Response(200, json=[{"boundingbox": ["33.5", "33.8", "72.8", "73.2"]}]))
    respx.get(url__startswith=settings.overpass_url).mock(
        return_value=httpx.Response(200, json=json.loads(fixture("overpass_islamabad.json"))))
    respx.get("https://www.zarafabrics.pk/").mock(return_value=_html(fixture("retailer_home.html")))
    respx.get("https://www.zarafabrics.pk/pages/about-us").mock(return_value=_html(fixture("retailer_about.html")))
    respx.get("https://www.zarafabrics.pk/pages/contact-us").mock(return_value=_html(fixture("retailer_contact.html")))
    respx.get("https://pixeldigital.pk/").mock(return_value=_html(fixture("agency_home.html")))
    respx.get("https://comingsoon-traders.pk/").mock(return_value=_html(fixture("thin_home.html")))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))


async def _run(campaign, settings, defaults, verdict):
    _mock_world(settings)
    campaign.geography.cities = ["Islamabad"]
    db = Database(settings.database_url)
    async with HttpFetcher(settings) as fetcher:
        pipeline = Pipeline(settings, defaults, db, fetcher, mx=FakeMX())
        pipeline.llm = RoutingLLM(verdict)   # turn the LLM layer on for this run
        result = await pipeline.run(campaign)
    db.close()
    return {l.company_name: l for l in result.leads}


@respx.mock
async def test_intent_verdict_is_recorded_on_the_lead(campaign, settings, defaults):
    by_name = await _run(campaign, settings, defaults,
                         {"buyer": True, "confidence": 0.9, "reason": "runs retail outlets, manual stock"})
    zara = by_name["Zara Fabrics"]
    assert zara.intent_fit is True
    assert zara.intent_confidence == 0.9
    assert "stock" in zara.intent_reason
    assert "intent_fit" in zara.provenance


@respx.mock
async def test_confident_non_buyer_verdict_demotes_the_retailer(campaign, settings, defaults):
    # The retailer keyword-classifies as BUYER; a confident "not a buyer" intent verdict must
    # pull it out of BUYER, proving intent – not keywords – has the final say.
    by_name = await _run(campaign, settings, defaults,
                         {"buyer": False, "confidence": 0.9, "reason": "no evident need"})
    zara = by_name["Zara Fabrics"]
    assert zara.intent_fit is False
    assert zara.company_type == CompanyType.UNKNOWN
