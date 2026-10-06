"""Adversarial coverage of the multi-tenancy boundary and campaign input validation.

The security claim is "one account can never reach another's campaigns or leads." A single
happy-path test does not establish that - a route that forgot its guard would slip through.
So this enumerates *every* campaign- and lead-scoped route and asserts a non-owner is refused
on each, that a refusal is a 404 (never a 403 that confirms existence, never a 500), and that
hostile campaign ids (path traversal, SQL, overlong, unicode) fall through to a clean 404.

DB-backed, so gated on GTM_TEST_DATABASE_URL like the rest of the suite.
"""

import pytest
from fastapi.testclient import TestClient

from conftest import bypass_auth
from gtm_engine.api.auth import current_user_id
from gtm_engine.models import CompanyType, EmailStatus, Lead, Priority
from gtm_engine.storage.database import Database


# Every campaign-scoped route, as (method, path-suffix, json-body). The guard runs before the
# body, so bodies here only need to be well-formed enough not to 422 before the guard fires.
CAMPAIGN_ROUTES = [
    ("get", "", None),
    ("get", "/stats", None),
    ("get", "/progress", None),
    ("get", "/leads", None),
    ("get", "/yaml", None),
    ("put", "/yaml", {"yaml": "campaign_id: {cid}\nname: X\noffer: y\n"}),
    ("get", "/export", None),
    ("post", "/export/sheets", {}),
    ("post", "/run", {}),
    ("delete", "", None),
    ("get", "/outreach/queue", None),
    ("post", "/outreach/send", {}),
    ("post", "/outreach/sync", {}),
    ("get", "/outreach/activity", None),
    ("get", "/outreach/sequence", None),
]

LEAD_ROUTES = [
    ("get", "", None),
    ("post", "/suppress", {}),
    ("post", "/review", {"verdict": "correct"}),
    ("post", "/referral", {"accept": True}),
    ("get", "/drafts/email_1", None),
    ("put", "/drafts/email_1", {"subject": "s", "body": "b"}),
    ("post", "/drafts/email_1/approve", None),
    ("post", "/drafts/email_1/reject", None),
    ("post", "/drafts/email_1/reset", None),
]


@pytest.fixture
def world(settings, tmp_path, monkeypatch):
    """user-a owns a campaign with one seeded lead; returns act_as + the ids. GitHub dispatch
    is stubbed so /run does not reach the network on the owner's happy path."""
    import gtm_engine.api.main as m
    monkeypatch.setattr(m, "_settings", settings)
    monkeypatch.setattr(m, "dispatch_workflow", lambda *a, **k: None)
    camp_dir = tmp_path / "campaigns"
    camp_dir.mkdir()
    monkeypatch.setattr(m, "CAMPAIGN_DIR", camp_dir)
    bypass_auth(m, monkeypatch)
    client = TestClient(m.app)

    def act_as(user_id):
        monkeypatch.setitem(m.app.dependency_overrides, current_user_id, lambda: user_id)
        return client

    act_as("user-a")
    cid = client.post("/campaigns", json={"name": "Acme retail", "offer": "inventory",
                                          "cities": ["Lahore"], "osm_categories": ["shop=clothes"]}).json()["campaign_id"]
    db = Database(settings.database_url)
    db.save_lead(Lead(campaign_id=cid, company_name="Co", domain="co.pk", company_type=CompanyType.BUYER,
                      total_score=80, priority=Priority.HIGH, contact_email="a@co.pk",
                      email_status=EmailStatus.MX_VALID, outreach_ready=True), "r", "co.pk")
    lead_id = db.list_leads(cid)[0].lead_id
    db.close()
    return act_as, cid, lead_id


def _call(client, method, url, body):
    return getattr(client, method)(url, **({"json": body} if body is not None else {}))


@pytest.mark.parametrize("method,suffix,body", CAMPAIGN_ROUTES)
def test_non_owner_is_refused_every_campaign_route(world, method, suffix, body):
    act_as, cid, _ = world
    b = body if body is None else {k: v.replace("{cid}", cid) if isinstance(v, str) else v for k, v in body.items()}
    r = _call(act_as("intruder"), method, f"/campaigns/{cid}{suffix}", b)
    assert r.status_code == 404, f"{method.upper()} /campaigns/{{id}}{suffix} leaked to a non-owner: {r.status_code}"


@pytest.mark.parametrize("method,suffix,body", LEAD_ROUTES)
def test_non_owner_is_refused_every_lead_route(world, method, suffix, body):
    act_as, _, lead_id = world
    r = _call(act_as("intruder"), method, f"/leads/{lead_id}{suffix}", body)
    assert r.status_code == 404, f"{method.upper()} /leads/{{id}}{suffix} leaked to a non-owner: {r.status_code}"


def test_owner_is_not_blocked_on_their_own_read_routes(world):
    act_as, cid, lead_id = world
    for suffix in ("", "/stats", "/progress", "/leads", "/outreach/sequence", "/outreach/activity"):
        assert act_as("user-a").get(f"/campaigns/{cid}{suffix}").status_code == 200, suffix
    assert act_as("user-a").get(f"/leads/{lead_id}").status_code == 200
    # /run reaches the (stubbed) dispatch rather than being blocked.
    assert act_as("user-a").post(f"/campaigns/{cid}/run", json={}).status_code == 200


@pytest.mark.parametrize("hostile", [
    "../../etc/passwd", "..%2f..%2fetc", "'; DROP TABLE campaigns;--", "%00", " ",
    "x" * 2000, "café-ünïçödé", "<script>alert(1)</script>", "a/b/c",
])
def test_hostile_campaign_id_is_a_clean_404_not_a_500(world, hostile):
    act_as, _, _ = world
    r = act_as("user-a").get(f"/campaigns/{hostile}/stats")
    # Never a 500: a hostile id must be "not found", not an internal error / injection.
    assert r.status_code in (404, 422), f"hostile id {hostile!r} returned {r.status_code}"


def test_unknown_lead_is_404_for_everyone(world):
    act_as, _, _ = world
    assert act_as("user-a").get("/leads/does-not-exist").status_code == 404
    assert act_as("intruder").get("/leads/does-not-exist").status_code == 404


def test_campaign_id_dedup_is_global_so_owners_cannot_collide(world):
    """Two owners creating the same name must get distinct ids - a shared id would let one
    read the other's campaign, and the owner check would be moot."""
    act_as, _, _ = world
    a = act_as("user-a").post("/campaigns", json={"name": "Shared Name", "offer": "x"}).json()["campaign_id"]
    b = act_as("user-b").post("/campaigns", json={"name": "Shared Name", "offer": "x"}).json()["campaign_id"]
    assert a != b
    # And each still cannot see the other's.
    assert act_as("user-b").get(f"/campaigns/{a}").status_code == 404
    assert act_as("user-a").get(f"/campaigns/{b}").status_code == 404


# Extreme / malformed input must be handled gracefully – never a 500. Since the input bounds
# landed (name/offer length, list caps, min_score 0-100, max_companies 1-1000), out-of-range
# values are rejected cleanly with 422 rather than silently clamped. A valid in-bounds body
# still succeeds (201). The invariant the test protects is "no 500 / no unbounded payload".
@pytest.mark.parametrize("body,expect", [
    ({"name": "N", "offer": "o", "min_score": -5}, 422),          # below the 0-100 range
    ({"name": "N", "offer": "o", "max_companies": 10**9}, 422),   # above the 1-1000 cap
    ({"name": "N" * 5000, "offer": "o"}, 422),                    # name over 200 chars
    ({"name": "N", "offer": "o", "cities": ["a"] * 500}, 422),    # list over its cap
    ({"name": "N", "offer": "o", "min_score": 80}, 201),          # in-bounds body still creates
    ({"name": "N"}, 422),                                          # offer missing
    ({"offer": "o"}, 422),                                         # name missing
    ({"name": "N", "offer": "o", "min_score": "high"}, 422),      # wrong type
])
def test_create_campaign_handles_extreme_and_malformed_input(world, body, expect):
    act_as, _, _ = world
    r = act_as("user-a").post("/campaigns", json=body)
    assert r.status_code == expect, r.text
    assert r.status_code != 500
