"""Tests for the natural-language campaign parser and API endpoint."""

import pytest

from gtm_engine.campaign.nl_parser import (
    CampaignDraft,
    HardFilters,
    build_campaign_config,
    build_explanation,
    parse_intent,
)
from gtm_engine.config.schema import CampaignConfig


# ---------------------------------------------------------------------------
# Deterministic parser: geography
# ---------------------------------------------------------------------------

def test_extract_cities_from_text():
    draft = parse_intent("find grocery stores in Islamabad and Lahore")
    assert "Islamabad" in draft.cities
    assert "Lahore" in draft.cities


def test_extract_single_city():
    draft = parse_intent("restaurants in Karachi that need POS software")
    assert draft.cities == ["Karachi"]


def test_no_city_defaults_pakistan():
    draft = parse_intent("I sell inventory software to grocery stores")
    assert draft.cities == []
    cfg = build_campaign_config(draft)
    assert cfg.geography.countries == ["Pakistan"]


def test_extract_province():
    draft = parse_intent("find retailers across Punjab and Sindh")
    assert "Punjab" in draft.provinces
    assert "Sindh" in draft.provinces


# ---------------------------------------------------------------------------
# Deterministic parser: offer extraction
# ---------------------------------------------------------------------------

def test_extract_offer_i_sell():
    draft = parse_intent("find stores in Islamabad. I sell inventory management software.")
    assert draft.offer is not None
    assert "inventory" in draft.offer.lower()


def test_extract_offer_we_offer():
    draft = parse_intent("we offer point-of-sale solutions to retailers in Lahore")
    assert draft.offer is not None
    assert "point-of-sale" in draft.offer.lower()


def test_extract_offer_providing():
    draft = parse_intent("providing ERP solutions to manufacturing companies")
    assert draft.offer is not None
    assert "erp" in draft.offer.lower()


def test_no_offer_uses_sectors_for_offer():
    text = "grocery stores in Islamabad"
    draft = parse_intent(text)
    assert draft.offer is None
    cfg = build_campaign_config(draft)
    assert "grocery" in cfg.offer.lower()
    assert "Islamabad" in cfg.offer


def test_bare_location_gets_sensible_name():
    text = "in Lahore"
    draft = parse_intent(text)
    assert draft.offer is None
    cfg = build_campaign_config(draft)
    assert cfg.name == "Businesses in Lahore"
    assert cfg.offer == text


# ---------------------------------------------------------------------------
# Deterministic parser: sector matching
# ---------------------------------------------------------------------------

def test_grocery_sector_match():
    draft = parse_intent("find grocery stores and marts in Islamabad")
    assert "grocery_supermarket" in draft.sectors


def test_clothing_sector_match():
    draft = parse_intent("find clothing boutiques and fashion stores")
    assert "clothing_apparel" in draft.sectors


def test_multiple_sector_match():
    draft = parse_intent("target electronics and furniture shops in Lahore")
    assert "electronics" in draft.sectors
    assert "furniture_home" in draft.sectors


# ---------------------------------------------------------------------------
# Deterministic parser: exclusions
# ---------------------------------------------------------------------------

def test_exclude_terms():
    draft = parse_intent("find stores but ignore Imtiaz and Metro")
    assert "imtiaz" in draft.negative_keywords
    assert "metro" in draft.negative_keywords


def test_exclude_chains_flag():
    draft = parse_intent("skip big chains, focus on independent stores")
    assert draft.exclude_chains is True


def test_no_chains_phrase():
    draft = parse_intent("no chains like Imtiaz or Metro")
    assert draft.exclude_chains is True


# ---------------------------------------------------------------------------
# Deterministic parser: max_companies
# ---------------------------------------------------------------------------

def test_extract_max_companies():
    draft = parse_intent("find top 20 grocery stores in Islamabad")
    assert draft.max_companies == 20


def test_no_max_companies_default():
    draft = parse_intent("grocery stores in Islamabad")
    assert draft.max_companies is None
    cfg = build_campaign_config(draft)
    assert cfg.max_companies == 30


# ---------------------------------------------------------------------------
# Deterministic parser: review/places interest
# ---------------------------------------------------------------------------

def test_review_interest_triggers_places():
    draft = parse_intent("find places with lots of reviews but no website")
    assert draft.enable_places is True
    assert draft.enable_review_text is True


def test_no_review_interest():
    draft = parse_intent("find clothing stores in Lahore")
    assert draft.enable_places is False


# ---------------------------------------------------------------------------
# Deterministic parser: hard filters
# ---------------------------------------------------------------------------

def test_hard_filter_min_reviews():
    draft = parse_intent("only stores with more than 50 reviews in Islamabad")
    assert draft.hard_filters.min_google_reviews == 50


def test_hard_filter_no_website():
    draft = parse_intent("businesses without a website in Karachi")
    assert "no_website" in draft.hard_filters.require_online_gap


def test_hard_filter_no_app():
    draft = parse_intent("places with no app or online presence")
    assert "no_app" in draft.hard_filters.require_online_gap


def test_hard_filter_tier():
    draft = parse_intent("tier 1 only, near my office")
    assert draft.hard_filters.max_proximity_tier == 1


def test_hard_filters_as_dict():
    hf = HardFilters(min_google_reviews=10, max_proximity_tier=2, require_online_gap=["no_website"])
    d = hf.as_dict()
    assert d == {"min_google_reviews": 10, "max_proximity_tier": 2, "require_online_gap": ["no_website"]}


def test_empty_hard_filters_as_dict():
    hf = HardFilters()
    assert hf.as_dict() == {}


# ---------------------------------------------------------------------------
# Config assembly
# ---------------------------------------------------------------------------

def test_build_campaign_config_basic():
    draft = CampaignDraft(
        raw_text="find grocery stores in Islamabad",
        offer="inventory software",
        cities=["Islamabad"],
        sectors=["grocery_supermarket"],
    )
    cfg = build_campaign_config(draft)
    assert isinstance(cfg, CampaignConfig)
    assert cfg.offer == "inventory software"
    assert cfg.geography.cities == ["Islamabad"]
    assert cfg.geography.countries == ["Pakistan"]
    assert cfg.campaign_id  # non-empty


def test_build_campaign_config_dedupes_id():
    draft = CampaignDraft(raw_text="test campaign", offer="test")
    cfg1 = build_campaign_config(draft, existing_ids=set())
    cfg2 = build_campaign_config(draft, existing_ids={cfg1.campaign_id})
    assert cfg1.campaign_id != cfg2.campaign_id


def test_build_campaign_config_with_hard_filters():
    draft = CampaignDraft(
        raw_text="test",
        offer="test",
        hard_filters=HardFilters(min_google_reviews=50),
    )
    cfg = build_campaign_config(draft)
    assert cfg.hard_filters == {"min_google_reviews": 50}


def test_build_campaign_config_exclude_chains():
    draft = CampaignDraft(raw_text="test", offer="x", exclude_chains=True)
    cfg = build_campaign_config(draft)
    assert cfg.exclude_chains is True


# ---------------------------------------------------------------------------
# Explanation
# ---------------------------------------------------------------------------

def test_build_explanation():
    draft = CampaignDraft(
        raw_text="find grocery stores in Islamabad",
        offer="inventory software",
        cities=["Islamabad"],
        sectors=["grocery_supermarket"],
        enable_places=True,
    )
    cfg = build_campaign_config(draft)
    expl = build_explanation(draft, cfg)
    assert expl["offer_detected"] == "inventory software"
    assert expl["cities"] == ["Islamabad"]
    assert expl["sectors_matched"] == ["grocery_supermarket"]
    assert expl["enable_places"] is True


# ---------------------------------------------------------------------------
# LLM merge
# ---------------------------------------------------------------------------

def test_merge_llm_fills_gaps():
    from gtm_engine.campaign.nl_parser import _merge_llm

    draft = CampaignDraft(
        raw_text="test",
        offer="inventory software",
        cities=["Islamabad"],
    )
    llm_fields = {
        "target_industries": ["grocery", "retail"],
        "buyer_keywords": ["mart", "store"],
        "sectors": ["grocery_supermarket"],
    }
    _merge_llm(draft, llm_fields)
    assert "grocery" in draft.target_industries
    assert "mart" in draft.buyer_keywords
    assert "grocery_supermarket" in draft.sectors


def test_merge_llm_does_not_overwrite():
    from gtm_engine.campaign.nl_parser import _merge_llm

    draft = CampaignDraft(
        raw_text="test",
        offer="my software",
        cities=["Islamabad"],
    )
    llm_fields = {"offer": "their software", "cities": ["Lahore"]}
    _merge_llm(draft, llm_fields)
    assert draft.offer == "my software"  # deterministic wins
    assert draft.cities == ["Islamabad"]  # deterministic wins


def test_merge_llm_empty_dict():
    from gtm_engine.campaign.nl_parser import _merge_llm

    draft = CampaignDraft(raw_text="test")
    _merge_llm(draft, {})
    assert draft.offer is None  # unchanged


# ---------------------------------------------------------------------------
# LLM task (parse_campaign_nl)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_campaign_nl_no_llm():
    from gtm_engine.llm.tasks import parse_campaign_nl
    result = await parse_campaign_nl(None, "find stores", ["grocery_supermarket"])
    assert result == {}


# ---------------------------------------------------------------------------
# Full pipeline: build_campaign_from_nl
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_campaign_from_nl_no_llm():
    from gtm_engine.campaign.nl_parser import build_campaign_from_nl

    cfg, explanation = await build_campaign_from_nl(
        "find grocery stores in Islamabad. I sell inventory software. Ignore chains like Imtiaz."
    )
    assert isinstance(cfg, CampaignConfig)
    assert cfg.geography.cities == ["Islamabad"]
    assert "imtiaz" in cfg.negative_keywords
    assert explanation["offer_detected"] is not None
    assert "grocery_supermarket" in explanation["sectors_matched"]


@pytest.mark.asyncio
async def test_build_campaign_from_nl_review_interest():
    from gtm_engine.campaign.nl_parser import build_campaign_from_nl

    cfg, explanation = await build_campaign_from_nl(
        "find popular stores with lots of reviews in Lahore. I sell POS software."
    )
    assert cfg.geography.cities == ["Lahore"]
    assert explanation["enable_places"] is True
    assert explanation["enable_review_text"] is True


# ---------------------------------------------------------------------------
# Hard filters on CampaignConfig schema
# ---------------------------------------------------------------------------

def test_hard_filters_roundtrip():
    """hard_filters survives CampaignConfig serialisation/deserialisation."""
    cfg = CampaignConfig(
        campaign_id="test",
        name="test",
        offer="x",
        hard_filters={"min_google_reviews": 50, "require_online_gap": ["no_website"]},
    )
    dumped = cfg.model_dump(mode="json")
    restored = CampaignConfig.model_validate(dumped)
    assert restored.hard_filters == {"min_google_reviews": 50, "require_online_gap": ["no_website"]}


# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client(settings, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from conftest import bypass_auth
    import gtm_engine.api.main as m
    monkeypatch.setattr(m, "_settings", settings)
    camp_dir = tmp_path / "campaigns"
    camp_dir.mkdir()
    monkeypatch.setattr(m, "CAMPAIGN_DIR", camp_dir)
    bypass_auth(m, monkeypatch)
    return TestClient(m.app)


def test_nl_endpoint_creates_campaign(api_client):
    resp = api_client.post("/campaigns/nl", json={"text": "find grocery stores in Islamabad"})
    assert resp.status_code == 201
    data = resp.json()
    assert "campaign_id" in data
    assert data["status"] == "draft"
    assert "config" in data
    assert "explanation" in data
    assert data["config"]["geography"]["cities"] == ["Islamabad"]


def test_nl_endpoint_empty_text(api_client):
    resp = api_client.post("/campaigns/nl", json={"text": ""})
    assert resp.status_code == 422


def test_nl_endpoint_with_exclusions(api_client):
    resp = api_client.post("/campaigns/nl", json={
        "text": "find clothing stores in Lahore but ignore chains like Khaadi and Gul Ahmed"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "khaadi" in data["config"]["negative_keywords"]


def test_nl_endpoint_campaign_persisted_in_db(api_client, settings):
    resp = api_client.post("/campaigns/nl", json={"text": "electronics shops in Rawalpindi"})
    assert resp.status_code == 201
    cid = resp.json()["campaign_id"]
    # Verify it's in the DB by fetching it via the campaigns list
    list_resp = api_client.get("/campaigns")
    assert any(c["campaign_id"] == cid for c in list_resp.json())


# ---------------------------------------------------------------------------
# Pipeline hard filters
# ---------------------------------------------------------------------------

def test_apply_hard_filters_min_reviews():
    from gtm_engine.pipeline import _apply_hard_filters
    from gtm_engine.models import Lead, CompanyType, EmailStatus, Priority

    def _make(review_count):
        return Lead(
            campaign_id="t", company_name="X", domain="x.pk",
            company_type=CompanyType.BUYER, total_score=50,
            priority=Priority.QUALIFIED,
            online_presence={"google_review_count": review_count},
        )

    leads = [_make(100), _make(30), _make(None)]
    result = _apply_hard_filters(leads, {"min_google_reviews": 50})
    assert len(result) == 1
    assert result[0].online_presence["google_review_count"] == 100


def test_apply_hard_filters_require_gap():
    from gtm_engine.pipeline import _apply_hard_filters
    from gtm_engine.models import Lead, CompanyType, Priority

    def _make(has_ecommerce):
        return Lead(
            campaign_id="t", company_name="X", domain="x.pk",
            company_type=CompanyType.BUYER, total_score=50,
            priority=Priority.QUALIFIED,
            online_presence={"has_ecommerce_site": has_ecommerce},
        )

    leads = [_make(True), _make(False)]
    result = _apply_hard_filters(leads, {"require_online_gap": ["no_website"]})
    assert len(result) == 1
    assert result[0].online_presence["has_ecommerce_site"] is False


def test_apply_hard_filters_max_tier():
    from gtm_engine.pipeline import _apply_hard_filters
    from gtm_engine.models import Lead, CompanyType, Priority

    def _make(tier_pts):
        return Lead(
            campaign_id="t", company_name="X", domain="x.pk",
            company_type=CompanyType.BUYER, total_score=50,
            priority=Priority.QUALIFIED,
            evidence={"score": {"proximity_tier": tier_pts}},
        )

    leads = [_make(15), _make(12), _make(8)]  # Tier 1, 2, 3
    result = _apply_hard_filters(leads, {"max_proximity_tier": 1})
    assert len(result) == 1


def test_apply_hard_filters_empty():
    from gtm_engine.pipeline import _apply_hard_filters
    from gtm_engine.models import Lead, CompanyType, Priority

    lead = Lead(
        campaign_id="t", company_name="X", domain="x.pk",
        company_type=CompanyType.BUYER, total_score=50,
        priority=Priority.QUALIFIED,
    )
    result = _apply_hard_filters([lead], {})
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Discovery relevance filter
# ---------------------------------------------------------------------------

def test_discovery_relevance_filter_drops_irrelevant():
    from gtm_engine.pipeline import _discovery_relevance_filter
    from gtm_engine.models import DiscoveredCompany

    companies = [
        DiscoveredCompany(name="Laser Equipment Co", category="shop=tools", source="osm"),
        DiscoveredCompany(name="Gloria Jeans Coffee", category="shop=coffee", source="osm"),
        DiscoveredCompany(name="Some Web Result", category=None, source="web_search"),
    ]
    kept, dropped = _discovery_relevance_filter(companies, ["laser", "equipment", "leveler"])
    assert dropped == 1
    assert len(kept) == 2
    names = [c.name for c in kept]
    assert "Laser Equipment Co" in names
    assert "Some Web Result" in names
    assert "Gloria Jeans Coffee" not in names


def test_discovery_relevance_filter_passes_matching_category():
    """User-configured categories bypass keyword check; derived ones do not."""
    from gtm_engine.pipeline import _discovery_relevance_filter
    from gtm_engine.models import DiscoveredCompany

    companies = [
        DiscoveredCompany(name="ABC Store", category="shop=tools", source="osm"),
    ]
    kept, dropped = _discovery_relevance_filter(
        companies, ["laser"], {"shop=tools"}, user_configured_categories=True)
    assert dropped == 0
    assert len(kept) == 1

    kept2, dropped2 = _discovery_relevance_filter(
        companies, ["laser"], {"shop=tools"}, user_configured_categories=False)
    assert dropped2 == 1
    assert len(kept2) == 0


def test_discovery_relevance_filter_noop_without_keywords():
    from gtm_engine.pipeline import _discovery_relevance_filter
    from gtm_engine.models import DiscoveredCompany

    companies = [
        DiscoveredCompany(name="Anything", category="shop=coffee", source="osm"),
    ]
    kept, dropped = _discovery_relevance_filter(companies, [])
    assert dropped == 0
    assert len(kept) == 1


def test_discovery_relevance_filter_passes_no_category():
    from gtm_engine.pipeline import _discovery_relevance_filter
    from gtm_engine.models import DiscoveredCompany

    companies = [
        DiscoveredCompany(name="Unknown Co", category=None, source="osm"),
    ]
    kept, dropped = _discovery_relevance_filter(companies, ["laser", "equipment"])
    assert dropped == 0
    assert len(kept) == 1


# ---------------------------------------------------------------------------
# Area proximity filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_area_proximity_filter_drops_distant_companies():
    from gtm_engine.pipeline import _area_proximity_filter
    from gtm_engine.models import DiscoveredCompany
    from unittest.mock import AsyncMock, patch
    from gtm_engine.discovery.geocode import BBox

    # G-13 Islamabad center approx: 33.6321, 73.0225
    g13_bbox = BBox(south=33.625, west=73.015, north=33.640, east=73.030)

    companies = [
        DiscoveredCompany(name="Near Clinic", source="osm", extra={"lat": 33.633, "lon": 73.023}),  # ~0.1km
        DiscoveredCompany(name="Far Hospital", source="osm", extra={"lat": 33.52, "lon": 73.10}),   # ~15km
        DiscoveredCompany(name="No Coords", source="osm"),  # no lat/lon – should pass
    ]

    with patch("gtm_engine.discovery.geocode.Geocoder") as MockGeocoder:
        instance = MockGeocoder.return_value
        instance.bbox = AsyncMock(return_value=g13_bbox)
        mock_fetcher = AsyncMock()
        mock_settings = AsyncMock()
        mock_settings.db_path.parent = AsyncMock()

        kept, dropped = await _area_proximity_filter(
            companies, ["G-13"], ["Islamabad"], mock_fetcher, mock_settings)

    assert dropped == 1
    assert len(kept) == 2
    names = [c.name for c in kept]
    assert "Near Clinic" in names
    assert "No Coords" in names
    assert "Far Hospital" not in names


@pytest.mark.asyncio
async def test_area_proximity_filter_noop_without_areas():
    from gtm_engine.pipeline import _area_proximity_filter
    from gtm_engine.models import DiscoveredCompany

    companies = [DiscoveredCompany(name="Anything", source="osm", extra={"lat": 33.5, "lon": 73.1})]
    kept, dropped = await _area_proximity_filter(companies, [], ["Islamabad"], None, None)
    assert dropped == 0
    assert len(kept) == 1


def test_sector_codes_extraction():
    from gtm_engine.pipeline import _sector_codes
    assert _sector_codes("Sachal Sarmast Road (G-11), Islamabad") == {"G-11"}
    assert _sector_codes("Savoy Arcade, 25 Hillal Rd, F-11 Markaz") == {"F-11"}
    assert _sector_codes("House 3, G-11/4 Islamabad") == {"G-11"}   # sub-sector -> parent
    assert _sector_codes("a 5 star hotel on Road 11") == set()       # no false positive
    assert _sector_codes(None) == set()


@pytest.mark.asyncio
async def test_area_proximity_filter_drops_wrong_sector_even_when_near():
    """A company whose ADDRESS names a different sector is dropped, even if its coordinates
    fall within the radius of the requested sector's centre (adjacent sectors overlap)."""
    from gtm_engine.pipeline import _area_proximity_filter
    from gtm_engine.models import DiscoveredCompany
    from unittest.mock import AsyncMock, patch
    from gtm_engine.discovery.geocode import BBox

    g13_bbox = BBox(south=33.625, west=73.015, north=33.640, east=73.030)
    companies = [
        DiscoveredCompany(name="G-13 Clinic", source="osm", address="Markaz G-13, Islamabad",
                          extra={"lat": 33.633, "lon": 73.023}),
        DiscoveredCompany(name="F-11 Clinic", source="overture", address="F-11 Markaz, Islamabad",
                          extra={"lat": 33.634, "lon": 73.024}),  # coords near G-13 but sector F-11
    ]
    with patch("gtm_engine.discovery.geocode.Geocoder") as MockGeocoder:
        instance = MockGeocoder.return_value
        instance.bbox = AsyncMock(return_value=g13_bbox)
        settings = AsyncMock()
        settings.anchor_lat = None
        settings.db_path.parent = AsyncMock()
        kept, dropped = await _area_proximity_filter(
            companies, ["G-13"], ["Islamabad"], AsyncMock(), settings)

    names = [c.name for c in kept]
    assert "G-13 Clinic" in names
    assert "F-11 Clinic" not in names
    assert dropped == 1


def test_geofence_adapts_to_area_size():
    """The geofence is derived from each area's geocoded extent at run time: a point/dense
    block stays tight (floored, never city-wide); a wide neighbourhood scales up – no per-city
    radius tuning."""
    from gtm_engine.pipeline import _fence_from_bbox
    from gtm_engine.discovery.geocode import BBox
    from gtm_engine.scoring.proximity import haversine_km

    def dims(f):
        return (haversine_km(f.south, f.clon, f.north, f.clon),
                haversine_km(f.clat, f.west, f.clat, f.east))

    tight_h, tight_w = dims(_fence_from_bbox(BBox(south=31.5200, west=74.3400, north=31.5205, east=74.3405)))
    wide_h, wide_w = dims(_fence_from_bbox(BBox(south=31.46, west=74.26, north=31.505, east=74.31)))
    assert tight_h < 2.5 and tight_w < 2.5     # a dense block stays tight, not city-wide
    assert wide_h > 4 and wide_w > 4           # a wide neighbourhood scales up
    assert wide_h > tight_h and wide_w > tight_w


def test_area_regex_excludes_motorways_and_highways():
    """Letter-digit tokens that are NOT residential sectors must not be read as areas, or they
    geofence a run down to nothing: motorways (M-2), highways (N-5), cricket/summit (T-20/G-20)."""
    assert parse_intent("auto workshops near M-2 motorway Lahore").areas == []
    assert parse_intent("sports shops for T-20 cricket in Karachi").areas == []
    assert parse_intent("logistics firms on N-5 highway").areas == []
    # Real sectors still parse.
    assert "G-13" in parse_intent("dentists near G-13 Islamabad").areas
    assert "F-11" in parse_intent("clinics near F-11 Islamabad").areas


def test_city_matched_whole_word_not_substring():
    """A city name must match as a whole word: 'Hub' (a real city) must not fire on 'hubs'."""
    assert "Hub" not in parse_intent("tech startups in innovation hubs in Lahore").cities
    assert "Hub" in parse_intent("find shops in Hub Balochistan").cities


@pytest.mark.asyncio
async def test_area_filter_fails_open_when_it_would_drop_everything():
    """Systemic guard: if the area filter would drop EVERY company (a mis-parsed/mis-geocoded
    area), keep them unfiltered rather than return a silent empty run."""
    from gtm_engine.pipeline import _area_proximity_filter
    from gtm_engine.models import DiscoveredCompany
    from unittest.mock import AsyncMock, patch
    from gtm_engine.discovery.geocode import BBox

    g13 = BBox(south=33.625, west=73.015, north=33.640, east=73.030)
    companies = [  # both far from G-13 (Karachi, Lahore) – would all be dropped without the guard
        DiscoveredCompany(name="Far A", source="osm", extra={"lat": 24.86, "lon": 67.0}),
        DiscoveredCompany(name="Far B", source="overture", extra={"lat": 31.52, "lon": 74.35}),
    ]
    with patch("gtm_engine.discovery.geocode.Geocoder") as MockGeocoder:
        MockGeocoder.return_value.bbox = AsyncMock(return_value=g13)
        settings = AsyncMock()
        settings.anchor_lat = None
        settings.db_path.parent = AsyncMock()
        kept, dropped = await _area_proximity_filter(companies, ["G-13"], ["Islamabad"], AsyncMock(), settings)
    assert len(kept) == 2 and dropped == 0


def test_city_token_not_extracted_as_area():
    """A word inside a recognised city name is not a separate area: 'Wah Cantt' is a city, so
    'Cantt' must not become an area (that bogus geofence dropped every result -> empty run)."""
    draft = parse_intent("find veterinary clinics in Wah Cantt")
    assert draft.cities == ["Wah Cantt"]
    assert "Cantt" not in draft.areas and draft.areas == []
    # A genuine cantt area (not part of the city name) is still kept.
    draft2 = parse_intent("find clinics in Lahore Cantt")
    assert "Cantt" in draft2.areas


def test_areas_wired_into_geography():
    draft = parse_intent("find newspaper offices near G-7 Islamabad")
    cfg = build_campaign_config(draft)
    assert "G-7" in cfg.geography.areas


def test_areas_search_queries_include_area():
    draft = parse_intent("find grocery stores near F-11 Islamabad")
    cfg = build_campaign_config(draft)
    assert any("F-11" in q for q in cfg.search_queries)


async def test_check_discovery_relevance_no_llm():
    from gtm_engine.llm.tasks import check_discovery_relevance

    companies = [{"name": "Metro EVs", "category": "shop=car"}]
    result = await check_discovery_relevance(None, "newspaper offices", companies)
    assert result == [True]


async def test_check_discovery_relevance_with_llm():
    from gtm_engine.llm.tasks import check_discovery_relevance

    class FakeLLM:
        name = "fake"
        async def complete(self, system, user, *, max_tokens=400):
            return '[true, false]'

    companies = [
        {"name": "Daily News Office", "category": "office=newspaper"},
        {"name": "Metro EVs", "category": "shop=car"},
    ]
    result = await check_discovery_relevance(FakeLLM(), "newspaper offices", companies)
    assert result == [True, False]


async def test_check_discovery_relevance_judges_beyond_first_batch():
    """Regression: the old single-batch version judged only the first 20 and silently passed
    the rest. Every company past #20 must still be judged, not auto-kept."""
    from gtm_engine.llm.tasks import check_discovery_relevance

    class AllFalseLLM:
        name = "fake"
        def __init__(self):
            self.calls = 0
        async def complete(self, system, user, *, max_tokens=400):
            self.calls += 1
            return "[" + ", ".join(["false"] * 20) + "]"

    llm = AllFalseLLM()
    companies = [{"name": f"Pharmacy {i}", "category": "overture=pharmacy"} for i in range(25)]
    result = await check_discovery_relevance(llm, "doctors", companies)
    assert result == [False] * 25      # none leak through – all 25 judged, not just the first 20
    assert llm.calls == 2              # 20 + 5, chunked


async def test_check_discovery_relevance_caps_token_spend():
    """Beyond MAX_JUDGED we stop calling the LLM; the remainder keeps its upstream pass (True)."""
    from gtm_engine.llm.tasks import check_discovery_relevance, _RELEVANCE_MAX_JUDGED

    class AllFalseLLM:
        name = "fake"
        def __init__(self):
            self.calls = 0
        async def complete(self, system, user, *, max_tokens=400):
            self.calls += 1
            return "[" + ", ".join(["false"] * 20) + "]"

    llm = AllFalseLLM()
    n = _RELEVANCE_MAX_JUDGED + 15
    companies = [{"name": f"X {i}", "category": "overture=pharmacy"} for i in range(n)]
    result = await check_discovery_relevance(llm, "doctors", companies)
    assert result[:_RELEVANCE_MAX_JUDGED] == [False] * _RELEVANCE_MAX_JUDGED
    assert result[_RELEVANCE_MAX_JUDGED:] == [True] * 15   # beyond the cap: upstream pass kept
    assert llm.calls == _RELEVANCE_MAX_JUDGED // 20


def test_relevance_target_desc_prefers_industries_then_sectors():
    from gtm_engine.pipeline import _relevance_target_desc

    # Explicit industries win.
    assert _relevance_target_desc(["dental clinics"], ["pharmacy_health"]) == "dental clinics"
    # No industries → fall back to the sector's human term, so offer-only runs still gate.
    assert _relevance_target_desc([], ["pharmacy_health"]) == "pharmacy"
    # Too-broad sectors give no useful target type.
    assert _relevance_target_desc([], ["general_retail", "_niche"]) is None
    assert _relevance_target_desc([], []) is None
