"""In-process concurrency and load testing of the API.

Runs against the real ASGI app via httpx's ASGITransport (no server is started), firing many
requests at once with asyncio so the routes execute concurrently in Starlette's threadpool,
each opening its own psycopg connection. This is where connection-pool exhaustion, cross-user
leakage under load, and races in the run-in-progress guard would show up - none of which a
serial test can see. DB-backed, so gated on GTM_TEST_DATABASE_URL.
"""

import asyncio
import time

import httpx
import pytest
from fastapi import Request
from httpx import ASGITransport

from gtm_engine.models import CompanyType, EmailStatus, Lead, Priority
from gtm_engine.storage.database import Database


@pytest.fixture
def app(settings, tmp_path, monkeypatch):
    """The ASGI app with auth stubbed to read the acting user from an X-Test-User header, so
    concurrent requests can act as different users at the same time."""
    import gtm_engine.api.main as m
    from gtm_engine.api.auth import verify_request
    monkeypatch.setattr(m, "_settings", settings)
    monkeypatch.setattr(m, "dispatch_workflow", lambda *a, **k: None)
    # These tests probe concurrency and scale, not the free-tier quota (which has its own
    # tests). Lift the caps so a 50-campaign dedup race and an 800-lead listing can run.
    monkeypatch.setattr(m, "FREE_MAX_CAMPAIGNS", 10_000)
    monkeypatch.setattr(m, "FREE_MAX_LEADS_PER_CAMPAIGN", 10_000)
    camp_dir = tmp_path / "campaigns"
    camp_dir.mkdir()
    monkeypatch.setattr(m, "CAMPAIGN_DIR", camp_dir)

    def fake_verify(request: Request):
        user = request.headers.get("x-test-user")
        if user:
            request.state.user = {"sub": user}
        return None

    monkeypatch.setitem(m.app.dependency_overrides, verify_request, fake_verify)
    return m.app


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _seed_leads(dsn: str, campaign_id: str, n: int) -> None:
    db = Database(dsn)
    for i in range(n):
        db.save_lead(Lead(campaign_id=campaign_id, company_name=f"Co {i}", domain=f"co{i}.pk",
                          company_type=CompanyType.BUYER, total_score=50 + (i % 50), priority=Priority.QUALIFIED,
                          contact_email=f"c{i}@co{i}.pk", email_status=EmailStatus.MX_VALID), "r", f"co{i}.pk")
    db.close()


def test_concurrent_reads_stay_isolated_and_error_free(app, settings):
    """100 interleaved requests from two accounts: every response is 200 and never contains
    the other account's campaign. A leak under concurrency (shared state, a mis-scoped query)
    would show here even though the serial isolation test passes."""
    async def run():
        async with _client(app) as c:
            a = (await c.post("/campaigns", json={"name": "Alpha co", "offer": "x"},
                              headers={"x-test-user": "user-a"})).json()["campaign_id"]
            b = (await c.post("/campaigns", json={"name": "Beta co", "offer": "x"},
                              headers={"x-test-user": "user-b"})).json()["campaign_id"]

            async def one(user, mine, theirs):
                r = await c.get("/campaigns", headers={"x-test-user": user})
                assert r.status_code == 200
                ids = {x["campaign_id"] for x in r.json()}
                assert mine in ids and theirs not in ids
                return True

            tasks = []
            for i in range(100):
                if i % 2 == 0:
                    tasks.append(one("user-a", a, b))
                else:
                    tasks.append(one("user-b", b, a))
            return await asyncio.gather(*tasks)

    results = asyncio.run(run())
    assert len(results) == 100 and all(results)


def test_concurrent_distinct_creates_all_get_unique_ids(app):
    """50 campaigns created at once for one account: all succeed and every id is distinct.
    The slug de-dupe reads existing ids per request, so a race would hand two of them the
    same id and one would silently overwrite the other."""
    async def run():
        async with _client(app) as c:
            tasks = [c.post("/campaigns", json={"name": f"Camp {i}", "offer": "x"},
                            headers={"x-test-user": "user-a"}) for i in range(50)]
            resps = await asyncio.gather(*tasks)
            assert all(r.status_code == 201 for r in resps)
            ids = [r.json()["campaign_id"] for r in resps]
            listed = await c.get("/campaigns", headers={"x-test-user": "user-a"})
            return ids, {x["campaign_id"] for x in listed.json()}

    ids, listed_ids = asyncio.run(run())
    assert len(set(ids)) == len(ids), f"duplicate campaign ids under concurrency: {ids}"
    assert set(ids) <= listed_ids, "a concurrently-created campaign was lost"


def test_concurrent_run_dispatch_never_500s(app):
    """Fire 12 runs at the same campaign at once. The active-run guard is best-effort (a
    read-then-dispatch, not atomic), so several may get through - but no request may 500, and
    at least one must be accepted. This pins down 'no crash under a dispatch stampede'."""
    async def run():
        async with _client(app) as c:
            cid = (await c.post("/campaigns", json={"name": "Runner", "offer": "x"},
                                headers={"x-test-user": "user-a"})).json()["campaign_id"]
            tasks = [c.post(f"/campaigns/{cid}/run", json={}, headers={"x-test-user": "user-a"})
                     for _ in range(12)]
            return await asyncio.gather(*tasks)

    resps = asyncio.run(run())
    codes = [r.status_code for r in resps]
    assert all(code in (200, 409, 429) for code in codes), f"a run dispatch crashed: {codes}"
    assert 200 in codes, "no run was accepted at all"


def test_bulk_lead_listing_scales(app, settings):
    """A campaign with 800 leads still lists quickly and respects the limit."""
    async def run():
        async with _client(app) as c:
            cid = (await c.post("/campaigns", json={"name": "Bulk", "offer": "x"},
                                headers={"x-test-user": "user-a"})).json()["campaign_id"]
            _seed_leads(settings.database_url, cid, 800)
            t0 = time.perf_counter()
            r = await c.get(f"/campaigns/{cid}/leads?limit=1000", headers={"x-test-user": "user-a"})
            elapsed = time.perf_counter() - t0
            body = r.json()
            return r.status_code, len(body["items"]), body["total"], elapsed

    status, count, total, elapsed = asyncio.run(run())
    assert status == 200 and count == 800 and total == 800
    assert elapsed < 15.0, f"listing 800 leads took {elapsed:.1f}s"


def test_concurrent_bulk_reads_do_not_exhaust_connections(app, settings):
    """40 concurrent stats+leads reads against a populated campaign: every one returns 200.
    If each request's Database() leaked its connection, Postgres would refuse partway through."""
    async def run():
        async with _client(app) as c:
            cid = (await c.post("/campaigns", json={"name": "Pool", "offer": "x"},
                                headers={"x-test-user": "user-a"})).json()["campaign_id"]
            _seed_leads(settings.database_url, cid, 100)
            tasks = []
            for _ in range(40):
                tasks.append(c.get(f"/campaigns/{cid}/stats", headers={"x-test-user": "user-a"}))
                tasks.append(c.get(f"/campaigns/{cid}/leads", headers={"x-test-user": "user-a"}))
            return await asyncio.gather(*tasks)

    resps = asyncio.run(run())
    assert all(r.status_code == 200 for r in resps), [r.status_code for r in resps if r.status_code != 200]