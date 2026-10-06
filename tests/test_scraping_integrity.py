"""Hardening: a 200 response is not proof of a live company site, and a harvested string
is not proof of an address. Each case here produced a confident, wrong lead before.

Direction: quality over quantity – when a signal cannot be trusted, drop the lead."""

import httpx
import pytest
import respx

from gtm_engine.models import DiscoveredCompany, Priority
from gtm_engine.pipeline import Pipeline
from gtm_engine.scraping.fetcher import HttpFetcher
from gtm_engine.scraping.integrity import check, is_parked, is_placeholder, is_soft_404, looks_binary, redirect_target
from gtm_engine.scraping.site_crawler import SiteCrawler
from gtm_engine.storage.database import Database
from gtm_engine.validation.domains import canonical_domain
from gtm_engine.validation.emails import extract_emails

REAL = "<html><head><title>Zara Fabrics</title></head><body>" + "Zara Fabrics is a clothing retailer with six outlets across Islamabad. " * 8 + "</body></html>"


def _html(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/html"})


# --- individual detectors -------------------------------------------------------------

@pytest.mark.parametrize("text,title,hit", [
    ("shop.pk is for sale! Buy this domain. Inquire now.", None, True),
    ("This domain is parked free, courtesy of GoDaddy", None, True),
    ("Welcome to nginx!", None, True),
    ("Our fabrics are for sale in six outlets. " * 40, "Zara Fabrics", False),   # long shop page, not parked
])
def test_parked_detection(text, title, hit):
    assert bool(is_parked(text, title)) is hit


@pytest.mark.parametrize("text,hit", [
    ("404 - Page Not Found. The page you requested does not exist.", True),
    ("Nothing found for that address", True),
    ("Our 404 policy is explained in our returns page. " * 40, False),          # long page mentioning 404
])
def test_soft_404_detection(text, hit):
    assert bool(is_soft_404(text)) is hit


def test_placeholder_and_binary():
    assert is_placeholder("Coming soon. Our website is under construction.")
    assert not is_placeholder("Coming soon: our new winter collection. " * 50)   # a real shop teasing stock
    assert looks_binary("%PDF-1.7 ...") and not looks_binary(REAL)


def test_redirect_target():
    assert redirect_target("https://old.pk/", "https://new.com/x") == "new.com"
    assert redirect_target("https://shop.pk/", "https://www.shop.pk/home") is None   # same domain
    assert redirect_target("https://shop.pk/", "https://shop.pk:443/") is None


def test_check_prefers_the_true_reason():
    # a marketplace redirect is reported as such, not as "thin"
    r = check("https://old.pk/", "https://www.daraz.pk/shop/123", "<html>x</html>", "tiny")
    assert r.reason == "off_domain_not_own" and r.final_domain == "daraz.pk" and not r.usable
    ok = check("https://shop.pk/", "https://shop.pk/", REAL, "Zara Fabrics is a clothing retailer " * 8, "Zara Fabrics")
    assert ok.ok and ok.usable and ok.final_domain is None
    # a brand that genuinely moved is usable, with the move recorded
    moved = check("https://old.pk/", "https://zarafabrics.com/", REAL, "Zara Fabrics is a clothing retailer " * 8, "Zara")
    assert moved.ok and moved.final_domain == "zarafabrics.com" and "redirects to" in moved.notes[0]


# --- crawler rejects them -------------------------------------------------------------

@respx.mock
@pytest.mark.parametrize("body,reason", [
    ("<html><body><h1>parked.pk is for sale!</h1><p>Buy this domain.</p></body></html>", "parked"),
    ("<html><body><h1>404 - Page Not Found</h1></body></html>", "soft_404"),
    ("<html><body><h1>Coming soon</h1><p>Our site is under construction.</p></body></html>", "placeholder"),
    ("%PDF-1.7 binary", "binary"),
    ("<html><body>hi</body></html>", "thin"),
])
async def test_crawler_rejects_dead_sites(settings, body, reason):
    respx.get("https://x.pk/").mock(return_value=_html(body))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    async with HttpFetcher(settings) as f:
        snap = await SiteCrawler(f, 3).crawl("https://x.pk")
    assert not snap.reachable and snap.integrity_reason == reason and snap.integrity_detail


@respx.mock
async def test_crawler_accepts_a_real_site(settings):
    respx.get("https://x.pk/").mock(return_value=_html(REAL))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    async with HttpFetcher(settings) as f:
        snap = await SiteCrawler(f, 3).crawl("https://x.pk")
    assert snap.reachable and snap.integrity_reason is None


@respx.mock
async def test_marketplace_redirect_is_not_a_website(settings):
    respx.get("https://old.pk/").mock(return_value=httpx.Response(302, headers={"location": "https://www.daraz.pk/shop/9"}))
    respx.get("https://www.daraz.pk/shop/9").mock(return_value=_html(REAL))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    async with HttpFetcher(settings) as f:
        snap = await SiteCrawler(f, 3).crawl("https://old.pk")
    assert not snap.reachable and snap.integrity_reason == "off_domain_not_own" and snap.redirected_to == "daraz.pk"


@respx.mock
async def test_genuine_move_keeps_content_and_records_new_domain(settings):
    respx.get("https://old.pk/").mock(return_value=httpx.Response(301, headers={"location": "https://zarafabrics.com/"}))
    respx.get("https://zarafabrics.com/").mock(return_value=_html(REAL))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    async with HttpFetcher(settings) as f:
        snap = await SiteCrawler(f, 3).crawl("https://old.pk")
    assert snap.reachable and snap.redirected_to == "zarafabrics.com"


# --- fetcher: size cap --------------------------------------------------------------------

@respx.mock
async def test_response_size_is_capped(settings):
    settings.max_response_bytes = 50_000
    respx.get("https://huge.pk/").mock(return_value=_html("<html><body>" + "x" * 2_000_000 + "</body></html>"))
    async with HttpFetcher(settings) as f:
        r = await f.get("https://huge.pk/")
    assert r.truncated and len(r.text) <= 50_000 and r.ok


# --- emails: homoglyphs and junk ------------------------------------------------------------

def test_homoglyph_email_is_rejected_not_mangled():
    assert extract_emails("contact іnfo@shop.pk today") == []          # Cyrillic i
    assert extract_emails("contact info@shop.pk today") == ["info@shop.pk"]
    assert extract_emails("word-boundary:info@shop.pk") == ["info@shop.pk"]  # punctuation before is fine
    assert extract_emails("xinfo@shop.pk") == ["xinfo@shop.pk"]              # a real local part, kept
    assert extract_emails("​info@shop.pk") == []                          # zero-width char glued on


def test_idn_domains_fold_to_punycode():
    assert canonical_domain("https://اردو.pk/") == "xn--mgbqf7g.pk"
    assert canonical_domain("https://xn--mgbqf7g.pk/") == "xn--mgbqf7g.pk"
    assert canonical_domain("https://WWW.SHOP.PK./") == "shop.pk"


# --- pipeline: a rejected site never becomes a qualified lead ---------------------------------

class FakeMX:
    async def has_mx(self, domain: str) -> bool:
        return True


@respx.mock
async def test_parked_site_cannot_produce_a_qualified_lead(campaign, settings, defaults):
    respx.get("https://parked.pk/").mock(return_value=_html("<html><body><h1>parked.pk is for sale</h1></body></html>"))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    campaign.osm_categories, campaign.overture_categories = [], []
    db = Database(settings.database_url)

    async def fake_discover(_c, _p=None):
        return [DiscoveredCompany(name="Parked Traders", website="https://parked.pk", city="Islamabad",
                                  country="Pakistan", source="osm")]

    async with HttpFetcher(settings) as fetcher:
        p = Pipeline(settings, defaults, db, fetcher, mx=FakeMX())
        p.discover = fake_discover
        result = await p.run(campaign)
    lead = result.leads[0]
    assert result.stats.rejected_sites == 1
    assert lead.company_type.value == "UNKNOWN" and not lead.outreach_ready
    assert "parked" in lead.provenance["website_rejected"]
    assert lead.priority in (Priority.REVIEW, Priority.REJECT)
    db.close()


# --- a dead or hostile host must not consume the batch ------------------------------------

@respx.mock
async def test_host_circuit_breaker_stops_hammering_a_dead_host(settings):
    settings.host_failure_limit = 2
    settings.max_retries = 0
    route = respx.get(url__regex=r"https://dead\.pk/.*").mock(side_effect=httpx.ConnectError("boom"))
    async with HttpFetcher(settings) as f:
        errors = [(await f.get(f"https://dead.pk/{i}")).error for i in range(5)]
    assert errors[:2] == ["http_error:ConnectError"] * 2
    assert errors[2:] == ["host_unavailable"] * 3      # breaker open: no further requests
    assert route.call_count == 2


@respx.mock
async def test_blocked_host_is_recorded_not_disguised(settings):
    """A 403 means the site refuses this client. We record it; we do not spoof a browser."""
    sent = []

    def handler(request):
        sent.append(request.headers.get("user-agent"))
        return httpx.Response(403, text="Forbidden")
    respx.get(url__regex=r"https://wall\.pk/.*").mock(side_effect=handler)
    async with HttpFetcher(settings) as f:
        r1 = await f.get("https://wall.pk/")
        r2 = await f.get("https://wall.pk/about")
    assert r1.error == "blocked" and r1.status_code == 403
    assert len(set(sent)) == 1 and "GTMLeadEngine" in sent[0]   # one honest identity throughout
    assert r2.error in ("blocked", "host_unavailable")


@respx.mock
async def test_recovered_host_clears_the_breaker(settings):
    settings.host_failure_limit = 3
    settings.max_retries = 0
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise httpx.ConnectError("flaky")
        return httpx.Response(200, text=REAL, headers={"content-type": "text/html"})
    respx.get(url__regex=r"https://flaky\.pk/.*").mock(side_effect=handler)
    async with HttpFetcher(settings) as f:
        await f.get("https://flaky.pk/1")
        await f.get("https://flaky.pk/2")
        good = await f.get("https://flaky.pk/3")
        after = await f.get("https://flaky.pk/4")
    assert good.ok and after.ok        # a success resets the failure count


@respx.mock
async def test_two_records_redirecting_to_one_site_are_one_lead(campaign, settings, defaults):
    respx.get("https://alias.pk/").mock(return_value=httpx.Response(301, headers={"location": "https://zarafabrics.com/"}))
    respx.get("https://zarafabrics.com/").mock(return_value=_html(REAL))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    campaign.osm_categories, campaign.overture_categories = [], []
    db = Database(settings.database_url)

    async def fake_discover(_c, _p=None):
        return [DiscoveredCompany(name="Zara Fabrics", website="https://zarafabrics.com", city="Islamabad",
                                  country="Pakistan", source="osm"),
                DiscoveredCompany(name="Zara Fabrics Outlet", website="https://alias.pk", city="Islamabad",
                                  country="Pakistan", source="osm")]

    async with HttpFetcher(settings) as fetcher:
        p = Pipeline(settings, defaults, db, fetcher, mx=FakeMX())
        p.discover = fake_discover
        result = await p.run(campaign)
    assert result.stats.duplicates == 1 and len(result.leads) == 1
    assert result.leads[0].domain == "zarafabrics.com"
    db.close()


@respx.mock
async def test_mismatched_website_contributes_no_contact_details(campaign, settings, defaults):
    """A site that belongs to someone else must not lend this company its email or phone."""
    other = ("<html><head><title>Islamabad Inns Blog</title></head><body>"
             + "Islamabad Inns is a guest house blog. Call 0300 1112222 or write to owner@islamabadinns.com. " * 6
             + "</body></html>")
    respx.get("https://islamabadinns.wordpress.com/").mock(return_value=_html(other))
    respx.get(url__regex=r".*").mock(return_value=httpx.Response(404))
    campaign.osm_categories, campaign.overture_categories = [], []
    db = Database(settings.database_url)

    async def fake_discover(_c, _p=None):
        return [DiscoveredCompany(name="D-12 Markaz", website="https://islamabadinns.wordpress.com",
                                  city="Islamabad", country="Pakistan", source="overture")]

    async with HttpFetcher(settings) as fetcher:
        p = Pipeline(settings, defaults, db, fetcher, mx=FakeMX())
        p.discover = fake_discover
        result = await p.run(campaign)
    lead = result.leads[0]
    assert lead.contact_email is None and lead.phone is None and lead.contact_name is None
    assert not lead.outreach_ready
    assert "does not appear to belong" in lead.provenance["website_rejected"]
    db.close()
