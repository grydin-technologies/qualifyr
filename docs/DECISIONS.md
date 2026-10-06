# Decisions

Record of technical and product decisions, newest first.

| Date | Decision | Why |
|------|----------|-----|
| 2026-09-22 | A reachable site is not a live company site: parked/for-sale, soft-404, placeholder, binary and marketplace-redirect pages are rejected and the lead is demoted (`scraping/integrity.py`) | Each produced a confident, wrong lead. Quality over quantity: drop rather than ship |
| 2026-09-22 | A site whose name does not match the company contributes **no** contact details (email, phone, staff names) or intent | A phone harvested from somebody else's website is worse than no phone |
| 2026-09-22 | 401/403/429 is recorded as `blocked`; the client identity is never disguised to get around it | The site is refusing this client; spoofing a browser would bypass an access control we said we would respect |
| 2026-09-22 | Per-host circuit breaker (3 consecutive failures) + per-company crawl deadline + 4 MB response cap | One dead, hostile or enormous host must not consume the batch's time or memory |
| 2026-09-22 | Emails glued to non-ASCII characters are discarded, not repaired; IDN domains fold to punycode | `іnfo@x.pk` (Cyrillic і) was being harvested as `nfo@x.pk`, an address that silently bounces |
| 2026-09-22 | GDELT news lookups are opportunistic: skipped when the rate-limit slot is busy | A bonus signal must never stall the pipeline behind a 5.5 s lock |
| 2026-09-18 | No Node.js in the engine; JS-only sites handled by an optional Python `PlaywrightFetcher` behind the existing `Fetcher` protocol, off by default | Node already serves the UI; a second runtime in the pipeline adds a serialisation boundary, a second test suite and CI install for zero lead-quality gain. 0 of ~60 live sites needed JS so far – turn on `enable_browser_fallback` when data says otherwise |
| 2026-09-17 | Overture Maps (DuckDB over public S3 parquet) added as primary discovery source; Dukotah/leadgen not adopted, only its mirror-fallback, inline name/title patterns and chain-exclusion ideas borrowed (MIT) | Islamabad trial: 24,969 places vs 665 in OSM, 12,792 with websites; leadgen itself targets US agencies with no buyer gate or outreach |
| 2026-09-17 | robots.txt is enforced for website crawling only, not for API endpoints (Overpass, search) | overpass-api.de disallows `/api/` for crawlers, but it is an API meant for programmatic queries; robots.txt governs crawlers |
| 2026-09-17 | A vendor term in the company *name* is decisive (VENDOR) regardless of buyer terms elsewhere | "Retail Growth Consultancy" mentions retail constantly; vendors serving our target industry are the main false-positive class |
| 2026-09-17 | Buyer/vendor matches weighted by location: name/title/meta/first 800 chars ×3, body ×1 | Retailer footers routinely say "designed by X digital marketing agency" |
| 2026-09-17 | SQLite for the core engine; Supabase considered for the UI/hosting phase | Spec is local-first and tests must run offline; storage is a thin repository with portable SQL so the swap is one module |
| 2026-09-17 | `httpx` + own polite fetcher instead of Crawlee | Phase 1 fetches ~5 pages per site; a `Fetcher` protocol lets Crawlee/Playwright slot in for JS-heavy sites later |
| 2026-09-17 | Stdlib `csv`/`sqlite3`/`argparse` over pandas/SQLAlchemy/typer | Spec rule: check stdlib before adding a dependency |
| 2026-09-17 | Primary spec = `GTM_Lead_Engine_Claude_Code_Spec.docx`; older spec's LinkedIn/theHarvester/Apollo suggestions dropped | ToS risk, paid tiers, and the primary spec forbids LinkedIn as a dependency |
| 2026-09-17 | Search fallback (DuckDuckGo HTML) accepts a website only if the company name is clearly in the domain or title | A wrong website is worse than none: it would qualify the wrong company |
