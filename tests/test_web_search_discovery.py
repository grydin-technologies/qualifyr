"""E2 web-search discovery: query derivation and the discovery source. Offline – no network
(search_web is monkeypatched) and no DB."""

import pytest

from gtm_engine.config.schema import CampaignConfig, EngineSettings, GeographyConfig
from gtm_engine.discovery import web_search as ws
from gtm_engine.discovery.targeting import _seed_queries, derive_discovery_targets, load_taxonomy
from gtm_engine.discovery.web_search import WebSearchDiscovery, _name_from_domain
from gtm_engine.llm.tasks import generate_search_queries
from gtm_engine.pipeline import _round_robin


class FakeLLM:
    name = "fake"

    def __init__(self, reply: str):
        self.reply = reply

    async def complete(self, system, user, *, max_tokens=400):
        return self.reply


# --- query derivation --------------------------------------------------------------------

def test_round_robin_interleaves_so_a_cap_samples_every_source():
    # A dense source (many items) must not drain a small cap before the others are reached.
    dense = [f"osm{i}" for i in range(100)]
    web = ["web1", "web2"]
    merged = _round_robin([dense, web])
    assert merged[:4] == ["osm0", "web1", "osm1", "web2"]   # web-search reached within the first few
    assert len(merged) == 102 and set(merged) == set(dense) | set(web)   # nothing lost
    assert _round_robin([]) == [] and _round_robin([[], []]) == []


def test_name_from_domain():
    assert _name_from_domain("acme-textiles.pk") == "Acme Textiles"
    assert _name_from_domain("khaadi.com") == "Khaadi"


def test_seed_queries_cross_industries_with_the_first_two_cities():
    q = _seed_queries(["retail", "apparel"], ["Lahore", "Karachi", "Multan"], [], {}, limit=8)
    assert "retail in Lahore" in q
    assert "apparel in Karachi" in q
    assert all("Multan" not in x for x in q)      # only the first two cities are used
    assert len(q) == len(set(q))                   # de-duped


def test_seed_queries_fall_back_to_sector_match_terms():
    taxonomy = {"clothing_apparel": {"match": ["clothing", "apparel"]}}
    q = _seed_queries(None, ["Lahore"], ["clothing_apparel"], taxonomy, limit=8)
    assert "clothing in Lahore" in q


async def test_generate_search_queries_without_llm_is_empty():
    assert await generate_search_queries(None, "inventory software") == []


async def test_generate_search_queries_parses_an_array():
    llm = FakeLLM('["multi-branch pharmacy chains in Lahore", "retail groups in Karachi"]')
    q = await generate_search_queries(llm, "pos software", "Lahore")
    assert "multi-branch pharmacy chains in Lahore" in q and len(q) <= 5


async def test_derive_targets_includes_search_queries_without_an_llm():
    t = await derive_discovery_targets("inventory software for clothing retailers", ["retail"],
                                       None, load_taxonomy(), cities=["Lahore"])
    assert t.search_queries and any("Lahore" in q for q in t.search_queries)


# --- the discovery source ----------------------------------------------------------------

async def test_web_search_discovery_filters_directories_social_and_dedupes(monkeypatch):
    results = {
        "q1": [("https://khaadi.com/", "Khaadi"),
               ("https://facebook.com/khaadi", "Khaadi on Facebook"),   # social -> dropped
               ("https://khaadi.com/about", "Khaadi – About")],         # same domain -> deduped
        "q2": [("https://yellowpages.pk/khaadi", "directory"),          # directory -> dropped
               ("https://outfitters.com.pk/", "Outfitters")],
    }

    async def fake_search(fetcher, settings, query, **kwargs):
        return results.get(query, [])

    monkeypatch.setattr(ws, "search_web", fake_search)
    campaign = CampaignConfig(campaign_id="c", name="C", offer="x",
                              geography=GeographyConfig(countries=["Pakistan"]),
                              search_queries=["q1", "q2"])
    out = [c async for c in WebSearchDiscovery(None, EngineSettings()).discover(campaign)]

    domains = [c.domain for c in out]
    assert "khaadi.com" in domains and "outfitters.com.pk" in domains
    assert "facebook.com" not in domains and "yellowpages.pk" not in domains
    assert domains.count("khaadi.com") == 1
    assert all(c.source == "websearch" and c.country == "Pakistan" for c in out)
    assert out[0].website == "https://khaadi.com"


async def test_web_search_discovery_respects_the_query_cap(monkeypatch):
    calls: list[str] = []

    async def fake_search(fetcher, settings, query, **kwargs):
        calls.append(query)
        return []

    monkeypatch.setattr(ws, "search_web", fake_search)
    settings = EngineSettings(web_search_max_queries_per_run=2)
    campaign = CampaignConfig(campaign_id="c", name="C", offer="x",
                              geography=GeographyConfig(), search_queries=["a", "b", "c", "d"])
    _ = [c async for c in WebSearchDiscovery(None, settings).discover(campaign)]
    assert calls == ["a", "b"]
