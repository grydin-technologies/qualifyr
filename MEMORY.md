# MEMORY – working tracker

Live state of the project: what is built, what is next, the architecture to implement
against, and facts we verified so nobody re-researches them. Read this top-to-bottom before
starting engine work.

- **`PLAN.md`** (repo root) – the product direction of record (2026-09-25 reframe). Overrides
  anything here on *direction*.
- **`docs/DIRECTION.md`** – CEO direction; **`docs/ROADMAP.txt`** – historical phases A–G.
- This file – the live "what's done / what's next / how it works / what we verified".

Last updated: 2026-10-05 (Open-source repo + Vercel env var fixes)

**2026-10-05 open-source collaboration repo (grydinteam/qualifyr):**
- **Two remotes:** `origin` = `Hasee10/qualifyr` (private), `grydinteam` = `grydinteam/qualifyr` (public).
  Push to both: `git push origin main && git push grydinteam main`.
- **Apache 2.0 license** + `CONTRIBUTING.md` added. `leads/` directory removed + gitignored (had 69
  CSVs with real business data).
- **Per-user API key resolution in GitHub Actions:** `scripts/resolve_user_keys.py` reads encrypted
  keys from Supabase, decrypts with Fernet, exports to `$GITHUB_ENV`. `gather-leads.yml` runs it
  when `user_id` input is non-empty. Repo-level secrets are fallback (present on Hasee10, absent on
  grydinteam – users bring their own).
- **Commit results restricted to Hasee10 only:** `gather-leads.yml` commit step has
  `github.repository == 'Hasee10/qualifyr'` guard. grydinteam runs produce artifacts only.
- **Free-tier tightened for shared compute:** daily run limit = 3 (was 25). Existing limits:
  3 campaigns, 10 leads each. `usage_counts` table is non-bypassable (deleting campaigns doesn't
  reset the counter).
- **GitHub Pages** enabled on grydinteam: Source = GitHub Actions, `pages.yml` deploys `site/`.

**Vercel env vars (qualifyr-green.vercel.app = grydinteam deployment):**
Both Hasee10 and grydinteam deployments share the SAME Supabase project for now.

| Variable | Type | Purpose |
|----------|------|---------|
| `GTM_DATABASE_URL` | secret | Postgres connection string (session pooler :5432 or transaction :6543) |
| `GTM_ENCRYPTION_KEY` | secret | Fernet key for encrypting user API keys at rest |
| `GTM_SUPABASE_URL` | secret | Supabase project URL (e.g. `https://xxx.supabase.co`) – auth JWT verification |
| `GTM_GITHUB_TOKEN` | secret | PAT for dispatching GitHub Actions workflows |
| `GTM_GITHUB_REPO` | secret | `owner/repo` for workflow dispatch target |
| `NEXT_PUBLIC_SUPABASE_URL` | public | Same as GTM_SUPABASE_URL – used by frontend Supabase client (build-time) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | public | Supabase anon/publishable key (build-time) |

**CRITICAL:** `NEXT_PUBLIC_*` vars are inlined at **build time**. Adding them after a build does
nothing – you must redeploy. `GTM_*` vars are runtime (serverless function env).

**401 redirect loop fix (2026-10-05):** `api.ts` `request()` only redirects to `/sign-in` on 401
when a token was actually sent (expired session). Without this guard, a missing Supabase config on
the frontend → no token sent → server 401 → redirect → loop.

**2026-10-04 leads UX + landing polish:**
- **Leads list is newest-first**: `list_leads(order=...)` – `"recent"` (updated_at DESC, the
  Leads page) vs `"score"` (default, dashboard top-buyers). `/leads` takes `order` + `q`.
- **Server-side lead search**: `/leads?q=` → `data_json ILIKE %q%` (spans all matching leads,
  not just the loaded page); frontend debounces 300ms. Pagination counts derive from the server
  `total` (was using current-page length). `count_leads`/`list_leads` share `_apply_lead_filters`.
  Composite indexes `(campaign_id, updated_at)` + `(campaign_id, total_score)` for speed.
- **Sign-up**: optional short-answer textbox restored → saved as `monetization_comment`
  preference (stashed in `localStorage[PENDING_MONETIZATION_COMMENT_KEY]`, flushed on first auth
  load like the vote). Admins read it from `user_preferences`.
- **Landing**: source marquee has no tiles (logos on the dark section; per-item margins make the
  `-50%` loop seamless); marketing nav links centered via a 3-col grid; app sidebar + favicon use
  the real `QualifyrMark` (app/icon.svg is a solid theme-adaptive tile, legible at 16px).

**2026-10-04 quality overhaul (shareable output):**
- `gtm_engine/enrichment/fieldclean.py` (NEW, 17 unit tests in `tests/test_fieldclean.py`):
  `clean_email` (fixes `%20contact@`, `03009502334info@` – wired into `extract_emails`),
  `clean_address` (first of concatenated, no newlines), `clean_description`
  (never nav-menu scrape; meta prose → research brief), `prefer_latin_name`
  (Urdu/Arabic → Latin page title), `humanize_industry`, `clean_reason`. Wired into
  `pipeline.process_company` (company_name/address/description).
- **Relevance**: LLM `check_discovery_relevance` now DROPS off-type map-sourced
  companies (was reorder-only) – the dentists→pharmacies fix; stricter prompt in `llm/tasks.py`.
- **Area proximity** (`pipeline._area_proximity_filter`): geocodes companies with no
  lat/lon too (web/chambers), sets `settings.anchor_lat/lon` from area centroid so
  proximity scoring is no longer "Tier 1 no anchor".
- **Area filter is now runtime-adaptive (2026-10-04b)** – no fixed radius, no per-city tuning:
  - **Sector-code text match** (`_sector_codes`, regex `[A-Za-z]-\d{1,2}`) is the exact primary
    rule: if a company's name/address names a sector, keep only when it's a requested sector –
    drops "F-11 Markaz"/"G-12" from a G-11 search even when coords sit next to G-11.
  - **Geofence from the geocoded bounding box** (`_Geofence`, `_fence_from_bbox`): each area's
    tolerance is derived from its own Nominatim bbox – tight for a dense Lahore block, wide for
    a large sector. Clamped by `AREA_MIN_HALF_KM=0.7` / `AREA_MAX_HALF_KM=10` / `AREA_MARGIN_KM=0.2`
    so a point-geocode isn't impossibly tight nor a vague match city-wide. `AREA_RADIUS_KM` is gone.
  - NOTE: fixes GEOGRAPHY only. Type-relevance is hardened separately (below).
- **Type-relevance hardening (2026-10-04c)** – the pharmacies / NUST-AI-labs-for-"doctors" leak:
  - **LLM gate batching bug fixed** (`llm/tasks.check_discovery_relevance`): it judged only the
    first 20 map-sourced companies and silently passed the rest (`True`-padded). Now judges ALL in
    chunks of 20 up to `_RELEVANCE_MAX_JUDGED=120` (token-bucket paced); beyond the cap the
    upstream keyword-filter pass is kept. This was the single biggest leak on any >20-company run.
  - **Gate now runs for offer-only campaigns** (`pipeline._relevance_target_desc`): target type =
    `target_industries` → else derived sector human-terms → else skip (so a campaign with an offer
    but no explicit industries still gets the strict type check; `general_retail`/`_niche` are too
    broad to discriminate on, so they skip).
  - **Taxonomy over-casting fixed at source** (`discovery_taxonomy.yaml`): `pharmacy_health.overture`
    was `[pharmacy, drugstore, health, medical]` – `medical` LIKE-matched `medical_research_institute`
    (NUST) and `health` matched anything. Now `[pharmacy, drugstore, clinic, doctor, dentist]`.
  - Tests: chunking judges past #20 + token cap; target-desc fallback; taxonomy specificity.
- **NL discovery hints now honoured (2026-10-05)** – the last relevance leak for the no-Brave
  workflow: the NL form shows "OSM categories" + "Search queries" hint fields, but `submitNL`
  only sent text+max_companies, so the backend re-derived broad categories (incl. pharmacy) and
  the user's tight doctor-only tags were discarded. Now `/campaigns/nl` (`CampaignNLRequest`)
  accepts `osm_categories` + `search_queries`; `create_campaign_nl` sets them on the cfg so the
  pipeline treats them as authoritative (`user_configured_categories` → derivation never
  broadens past them). Frontend `submitNL` + `api.createCampaignNL` send them. Test:
  `test_nl_honours_discovery_hints`.
  - ⚠️ Not yet live-verified on real Groq + real discovery – do a capped "doctors" run to confirm.
- **CSV**: default UI export is the **clean client-ready sheet** (`write_clean_csv`,
  human headers, no plumbing); `?full=1` = raw `CSV_COLUMNS`. Enums serialize as values.
  Download filename derives from campaign name, not the long id slug.
- **NL names**: `_name_from_draft` → short "<subject> - <area/city>"; `_extract_subject`
  drops verb clauses/generic nouns. Hard-filter parser recognizes "lack/without online presence".
- **UI**: settings drops Campaigns + Google Sheets tabs; sidebar status = connectivity only;
  campaign card title/stats click → Leads with that campaign selected.

**2026-10-04 free-tier limits + signup vote + UX:**
- **Free tier** (`api/main.py`, per signed-in user; local/self-host with `user_id=None`
  unlimited): `FREE_MAX_CAMPAIGNS=3`, `FREE_MAX_LEADS_PER_CAMPAIGN=10`, overridable via
  `GTM_FREE_MAX_CAMPAIGNS` / `GTM_FREE_MAX_LEADS_PER_CAMPAIGN`. Enforced in `create_campaign`
  + `create_campaign_nl` (403 at cap) and clamped (`_cap_leads`) at create and in
  `run_campaign`. Limits echoed on `/health` → New-campaign form reads the cap (not hardcoded).
  **Master accounts** (`UNLIMITED_EMAILS`, defaults to `ihaseebarshad10@gmail.com,hello@grydin.co`,
  override via `GTM_UNLIMITED_EMAILS`) are exempt from all quotas – matched on the token's
  `email` claim (`current_user_email`). `GET /settings/limits` returns the caller's effective
  caps (null = unlimited); the New-campaign form reads it instead of `/health`.
  Tests: `tests/test_free_tier_limits.py` (incl. master exemption + soft delete).
- **Soft delete (2026-10-05)**: deleting a campaign never hard-DELETEs – `campaigns.deleted_at`
  is stamped so the row (and its leads) stay in the DB permanently, for every account.
  `delete_campaign` → UPDATE deleted_at; `list_campaigns` filters `deleted_at IS NULL`;
  `all_campaign_ids()` (incl. deleted) de-dupes new ids so a recreate gets a fresh id and never
  resurrects a kept row. Soft-deleted campaigns free a free-tier slot (list excludes them).
- **CI fix (2026-10-05)**: `test_multitenancy_adversarial` expected extreme input → 201 (old
  "clamp" contract), but the security input bounds now reject with 422. Updated the test to
  expect 422 (graceful, never 500) + an in-bounds 201 case. This was the sole CI blocker.
- **Monetization vote** now mandatory on the sign-up form (required radio); saved after
  signup, stashed in `localStorage[PENDING_MONETIZATION_KEY]` and flushed on first
  authenticated load (campaign-context) for the e-mail-confirm flow. Removed from settings.
- **UI**: header campaign dropdown hidden on `/campaigns`; whole campaign card clickable →
  Leads (edit/delete/run stopPropagation).
- **Live run status** (fix "dispatched run shows as 'nothing ran' after navigation): provider
  (`campaign-context`) polls `refresh(true)` every 4s while any `campaign.live.stage` is active
  (app-level, survives navigation); `RunPanel` adopts fresh `campaign.live` on change (unless a
  local poll is mid-run); `RunPanel.start` calls `onFinished()` right after dispatch; Campaigns
  page force-refreshes on mount.
- **CI fix**: `tests/test_load_concurrency.py` – lift `FREE_MAX_*` in its fixture (concurrency
  tests, not quota), and `test_bulk_lead_listing_scales` reads `["items"]`/`["total"]` (the
  `/leads` endpoint returns `{items,total}` since the pagination change, not a bare list).
  NOTE: running two load-suites at once exhausts the shared Supabase pooler (pool_size 15) –
  run them once, not concurrently.

---

## 1. WHAT QUALIFYR IS (the reframe, now built)

An **offer-agnostic market-research search engine**, not a lead-gen / cold-email tool. You
describe what you sell → the engine derives what to search for → finds real companies from
free public sources → judges each by *need* → returns a small set of strictly-relevant
results, each with a research brief and a matched decision-maker. Campaigns and outreach are
secondary. Quality over quantity is absolute (3–5 great results = success).

Two intended jobs: (1) **market search** – "where can we sell this?"; (2) **competitor
analysis** – "what are my competitors doing?" (job 2 is **not built yet** – see E3).

The old "we sell websites" Phase-H pivot is now just **one possible offer** a user can type,
not the product.

---

## 2. WHAT IS BUILT (all ✅, pushed, CI green)

**Reframe priorities P1–P5:**
- **P1 Dynamic campaigns** – user-created, **DB-backed** (not files): create/list/delete/
  run-by-id, a New-campaign form, runs accumulate. `config.loader.resolve_campaign()` loads a
  campaign by id (DB) OR path (file); CLI `campaign-id` prints the resolved id for workflows.
- **P2 Hard filters + LLM keywords** – `llm/tasks.generate_keywords(offer)` +
  `qualification/relevance.relevant_terms`. Pipeline drops hiring/RFQ signals not relevant to
  the offer's **need-terms (not sector)** – the "Imtiaz was hiring, but not for us" fix.
  Generated keywords also feed PPRA discovery + the classifier; shown as chips; offer-relevant
  intent scores +3; `stats.intent_dropped_irrelevant` surfaced.
- **P3 Region filter** – `GeographyConfig.provinces` + `search_areas()`; OSM/Overture iterate
  areas and try each country as a geocode hint (one campaign can span countries). ⚠️ tension
  with the "Pakistan only" CEO directive – **needs sign-off** before real multi-country use.
- **P4 Result caps** – `max_companies` is the per-run cap ("API cap" in the form); plus
  `website_finder_max_per_run` bounds Brave.
- **P5 Research depth** – `enrichment/research.build_research_brief` (grounded per-company
  summary → `Lead.research_brief`, top of lead detail; includes a web-presence verdict for the
  thin/single-page case); decision-maker's own LinkedIn `/in/` profile extracted + matched by
  name (`parsers.personal_profiles`, `contacts._match_personal_profile`, needs BOTH names –
  never a stranger's).

**Intent-based matching (CEO: "leads strictly by intent, not keywords"), 4 slices done:**
- `llm/tasks.judge_intent(offer, evidence)` → grounded `{buyer, confidence, reason}`; None
  without an LLM. Wired via `pipeline.apply_intent_verdict` (threshold 0.6): a confident
  non-buyer demotes a keyword-only BUYER→UNKNOWN, a confident buyer promotes UNKNOWN→BUYER,
  VENDOR is never promoted. `scoring.score_lead` rewards evident need (×confidence). Stored on
  the lead (`intent_fit/intent_confidence/intent_reason`), shown as a badge + reason in the UI.
  `judge_intent` runs **once per non-vendor company** when the LLM is on (bounded by the cap).
- **The LLM layer is ENABLED**: `config/engine.yaml` → `enable_llm: true`, `llm_provider: groq`.

**Multi-tenancy** – campaigns carry `owner_id` (migrated via `ALTER TABLE ... ADD COLUMN IF
NOT EXISTS`), set on create from the Supabase token's `sub` (`auth.current_user_id`), preserved
on re-upsert via `COALESCE`. Every `/campaigns/{id}/…` route guarded by `require_campaign_access`,
every `/leads/{id}/…` by `require_lead_access` (both as decorator `dependencies=[…]`). A campaign
the caller may not see is **404, not 403** (existence not leaked). File-based example campaigns
and legacy NULL-owner rows stay **shared**. **No scoping when auth is off/bypassed** (local
operator, tests) – `current_user_id` is None. Suppressions + mailboxes are global operator infra.

**Golden set** – `gtm_engine/eval/golden.py` + `tests/golden/golden_leads.jsonl` (18 rows) +
`scripts/golden_eval.py`. `tests/test_golden_set.py` enforces accuracy floor 0.8 (baseline
100%) + hard invariants: an agency is never a buyer, a real retailer is never rejected. **The
seed is small – grow it to 50+, esp. intent-judge cases, to trust the number.**

**Phase 5 – Business profile enrichment** ✅ **DONE (2026-10-02):**
- Track A: OSM `opening_hours` extraction + structured parser (`enrichment/hours.py`)
- Track B: Google Places API (`enrichment/places.py`) – Text Search (unlimited free) + Place
  Details Enterprise for rating, review count, hours. Budget: 20/run, auto-enables when
  `GTM_GOOGLE_PLACES_API_KEY` is set. Key stored in GitHub Secrets only, never logged.
- Online presence audit: `enrichment/online_presence.py` – detects ecommerce, WhatsApp, social,
  delivery platforms, mobile app. `OnlinePresence` model with `online_gap_score` (inverse
  digital maturity). Gap labels: `no_website`, `no_app`, `no_whatsapp`, etc.

**Phase 6 – Decomposed scoring + pain mining** ✅ **DONE (2026-10-03):**
- Scoring reworked: `review_band(0-30) + rating(0-10) + proximity_tier(0-15) + online_gap(0-25)
  + pain_evidence(0-20) = max 100`. Replaces old 6-dimension ICP scoring.
- Proximity/tier: haversine from configurable anchor (`anchor_lat`/`anchor_lon`), Tier 1/2/3.
- Review text pain mining: keyword patterns + optional LLM refinement on Google review text.
- Config: `enable_review_text`, `anchor_lat`, `anchor_lon`, `proximity_tier1_km/2_km`.

**NL campaign interface** ✅ **DONE (2026-10-03):**
- `gtm_engine/campaign/nl_parser.py` – accepts text like "find grocery stores in Islamabad that
  need inventory software", auto-builds CampaignConfig. Two-stage: deterministic regex always
  runs, optional LLM fills gaps (never overwrites). `POST /campaigns/nl` + `gtm nl` CLI.
- **NL parser naming improvements:** sectors now used for campaign name/offer when no explicit
  offer given (e.g. "grocery stores in Islamabad" → "Find grocery supermarket businesses in
  Islamabad"). Bare location inputs ("in Lahore") produce "Businesses in Lahore" instead of
  using raw text as name. 49 NL tests passing.
- Frontend: **dual-mode adaptive form** – checks API keys on open:
  - Groq key present → NL text input (describe in plain English, engine handles the rest)
  - Groq absent → manual structured form (name, offer, industries, cities, keywords) + info
    banner nudging user to add Groq key in Settings
  - Brave absent (either mode) → extra fields for OSM categories / search queries
  - Example prompts shown in NL mode for quick start
- Editable `max_companies` field (default 30). "Run now" button in result panel triggers
  discovery immediately. `POST /campaigns/nl` accepts optional `max_companies` override.
- **Dark theme fix:** select dropdowns in settings page and campaign picker now use
  `bg-background`/`text-foreground` instead of `bg-transparent` (was white-on-white in dark mode).

**Frontend cleanup** ✅ **DONE (2026-10-03):**
- Campaigns page: compact cards (redundant offer line hidden when it matches name, sectors/keywords
  badges removed, stats in single row, smaller Run/CSV buttons, last-run shows date only).
- CSV export: authenticated fetch with bearer token (was broken – plain `<a href>` couldn't send auth).
- Self-serve mailbox management: Settings → Mailboxes tab (add SMTP credentials, test connection,
  enable/disable, delete). `user_mailboxes` table + 5 new API endpoints.
- React crash fix: NL explanation dict rendered as text node → guarded with type checks.

**Phase 7 – Open-source readiness** ✅ **DONE (2026-10-03):**
- Per-user API key management: `user_api_keys` table, Fernet-encrypted at rest (`GTM_ENCRYPTION_KEY`),
  resolution priority: user DB key → operator env var. `api/keys.py` + `api/usage.py`.
- Daily usage limits: `usage_counts` table, per-user caps (brave: 50, groq: 200, hunter: 10,
  places: 20). Configurable via `GTM_DAILY_LIMIT_{RESOURCE}`. Engine degrades to free fallbacks
  when limit hit.
- **User-adjustable limits:** users can change their own daily caps from Settings → Usage tab
  (inline edit, range 1 to 10× default). Stored in `user_preferences` as `daily_limit_{resource}`.
  Resolution priority: user preference → env var → default. `PUT /settings/usage/{resource}`.
- Settings UI: "API Keys" tab (save/delete/test per key, masked input, status badges) +
  "Usage" tab (progress bars per resource, editable limits, daily reset at UTC midnight).
- Monetization vote: `user_preferences` table, radio + comment in Settings; captures
  own-keys/managed-paid/undecided preference for product direction.
- CSV + Google Sheets deep link: after download, "View in Google Sheets" link on leads page.
- Key resolution wired into pipeline: `Pipeline(resolved_keys=...)` threads to search.py,
  client.py, verifier.py, places.py, web_search.py. CLI path unchanged (env vars only).
- **Adaptive campaign form:** "New campaign" sheet checks which API keys the user has configured
  and adapts the form accordingly:
  - Groq present → NL text input (auto mode: describe in plain English, engine handles the rest)
  - Groq absent → manual form: name, offer, industries, cities, keywords + info banner nudging
    toward adding a Groq key in Settings
  - Brave absent (either mode) → extra fields for OSM categories / search queries so the user
    can guide discovery manually when web search is unavailable
  - Places / Hunter / Gemini degrade silently – no extra form fields needed
  - NL mode submits to `POST /campaigns/nl`, manual mode to `POST /campaigns` (both pre-existing)
- 8 new API endpoints: `/settings/api-keys` (CRUD + test), `/settings/usage` (GET + PUT per
  resource), `/settings/preferences` (GET + PUT).
- `cryptography` added to core deps; `.env.example` updated with encryption key + limit overrides.
- Hard filters: `min_google_reviews`, `max_proximity_tier`, `require_online_gap` – applied
  post-scoring in the pipeline. City/province extraction from `config/defaults/pk_cities.yaml`.

**Post-discovery relevance filter** ✅ **DONE (2026-10-03):**
- `_discovery_relevance_filter()` in `pipeline.py` drops map-sourced companies (OSM/Overture)
  whose name, category, or address contain none of the offer's relevance keywords. Prevents
  broad OSM/Overture categories from flooding results with unrelated businesses (e.g. coffee
  shops when searching for laser land leveler dealers).
- Web-search, PPRA, KCCI, seed-CSV results pass automatically (query already targeted).
- Companies matching a campaign-requested category, or having no category, also pass.
- Stats: `discovery_relevance_dropped` count in RunStats, shown in progress message.
- 4 tests in `test_nl_campaign.py`.

**Campaign edit + delete UI** ✅ **DONE (2026-10-03):**
- Pencil icon on every campaign card opens an edit sheet with all config fields pre-filled
  (name, offer, industries, cities, keywords, OSM categories, search queries, max companies,
  min score). Saves via the existing YAML API (`PUT /campaigns/{id}/yaml`).
- Trash icon on every campaign card (including file-based examples). DB campaigns are deleted;
  file-based ones are hidden via `hidden_campaigns` table (filesystem is read-only on Vercel).
  `DELETE /campaigns/{id}` handles both cases.

**CI** – `ci.yml`: `test` job runs the DB-backed tests against a throwaway `postgres:16`
service (`GTM_TEST_DATABASE_URL`); `web` job runs `npm ci` + `next build` (tsc + ESLint). Both
green. **Local runs skip ~90 DB-gated tests** (no local Postgres); CI runs them all (~342).

**Landing page** – monochrome illustration pass; `web/src/components/marketing/illustration.tsx`
(one reused panel) in Features / How-it-works / Comparison / FAQ. Redundant ones removed.

---

## 3. ENGINE FOCUS – the current work stream (E1–E4)

**The finding that drives this:** the reframe was only *half*-built. Qualification got
reframed, but **discovery was still conventional lead-gen** – it ran ONLY on
`osm_categories`/`overture_categories` the user hand-picked in map-tag syntax; the offer/LLM
never drove *what* was searched, only filtered afterward. A campaign with an offer but no
categories discovered nothing, silently.

- **E1 – offer → discovery targets** ✅ **DONE + Phase 8 niche expansion.**
  `config/defaults/discovery_taxonomy.yaml` maps 16 sectors → valid OSM tags + Overture
  substrings. `discovery/targeting.derive_discovery_targets(offer, industries, llm)` picks
  sectors deterministically + LLM-widened. **Phase 8 addition:** when no taxonomy sector
  matches but `target_industries` exist, a **niche fallback** constructs valid OSM/Overture
  categories directly from the industry terms – validated against `config/defaults/valid_osm_tags.yaml`
  (~200 valid tags across shop/office/amenity/craft/healthcare/leisure/tourism). Synonym lookup +
  fuzzy matching + per-word decomposition. LLM can also suggest categories (validated against the
  same list). Result: "newspaper offices" → `office=newspaper`, not `shop=*`. "watch repair" →
  matches jewellery sector → `shop=watches`. "law firms" → `office=lawyer`. `_niche` pseudo-sector
  for niche matches. `pipeline.run()` derives categories when the user gave none; **explicit user
  categories always win**. `areas` field added to `GeographyConfig` and wired through NL parser →
  pipeline → targeting → seed queries (e.g. "newspaper offices G-7 Islamabad"). Post-discovery
  **LLM relevance check** (`check_discovery_relevance` in `llm/tasks.py`) demotes map-sourced
  companies the LLM flags as not matching the target type. Tests: `tests/test_discovery_targeting.py`
  (15 tests). Sectors → `stats.discovery_sectors`, shown as chips.
- **E2 – web-search discovery** ✅ **DONE.** `derive_discovery_targets` now also emits
  `search_queries` – deterministic seeds (industries/sector terms × cities) + optional LLM
  queries aimed at buyers (`llm/tasks.generate_search_queries`; queries are free text so the
  LLM writes them directly). `discovery/web_search.WebSearchDiscovery` runs them via the shared
  `search.search_web` (Brave when keyed, else keyless DuckDuckGo), takes each result's own
  domain, drops directories/aggregators/social, de-dupes, yields a company (asserts only the
  domain + a name from it; the pipeline crawls/classifies/intent-judges the rest, so
  competitors are filtered downstream). Config: `enable_web_search_discovery` (default on),
  `web_search_max_queries_per_run` (6); `CampaignConfig.search_queries`. Wired into `run()`
  (derives queries when the user set none; explicit map categories still win) + `discover()`.
  `max_companies` still caps what gets processed. Tests: `tests/test_web_search_discovery.py`
  (off in the DB fixture to stay hermetic). ⚠️ Not yet live-verified end-to-end on real Brave
  results – do a capped run to confirm quality before trusting it.
- **E3 – competitor-analysis flow** ⬜. The unbuilt 2nd core job: describe a product → find
  competitors → surface their hiring/press/funding. Different flow, larger build. **CEO earlier
  said park it – reconfirm before building.**
- **E4 – optimize** ✅ **mostly DONE** (was deliberately last):
  - **Proactive LLM token pacing** ✅ – `llm/client.TokenBucket` paces GroqLLM calls under the
    ~8k tokens/min free budget up front (was reactive 429-retry only). `GTM_GROQ_TOKENS_PER_MIN`.
  - **Async DB** ✅ – per-company DB calls run off the event loop via `pipeline._db_call`
    (`to_thread` + an asyncio lock; the single connection is not thread-safe). Progress writes
    get their OWN connection in `cli.py` so they never share the pipeline's under threads.
  - **DB reconnection** ✅ – every statement goes through `Database._execute`, which reconnects
    (backoff, search_path re-applied) once on a dropped connection; `_commit` recovers too.
  - **Nominatim** ✅ – explicit `geocode.NOMINATIM_DELAY_S` (1.1s, under the 1/sec public cap;
    disk-cached), `GTM_NOMINATIM_DELAY_S` to override for a self-hosted instance.
  - **Cron failure alert** ✅ – `gather-leads.yml` opens (or comments on) a `crawl-failure` issue
    on failure (keyless GITHUB_TOKEN).
  - ⬜ **Still open:** no in-code **Brave monthly spend counter** (documented in `docs/API_KEYS.md`);
    the async-DB win is real but DB calls are still **serialised** (one connection) – a true
    connection pool would parallelise them, if throughput ever demands it.

---

## 4. ARCHITECTURE & HOW TO WORK HERE

**Stack:** Python 3.12+ engine; FastAPI API (`gtm_engine/api/main.py`); Postgres via
`psycopg` (Supabase); Next.js 16 + Tailwind + shadcn frontend in `web/`. Deployed: frontend +
API on Vercel, crawls in GitHub Actions (`gather-leads.yml`), DB on Supabase.

**Where the core logic lives:**
- `pipeline.py` – the run: `run()` (setup: relevance kw, offer→targets, discover) →
  `discover()` (which sources fire) → `process_company()` (crawl → classify → intent judge →
  contacts → score → build lead). Per-company failures are isolated (one bad company ≠ dead run).
- `discovery/` – `targeting.py` (E1 offer→categories), `osm.py`, `overture.py` (category-gated),
  `chambers.py` (KCCI), `search.py` (WebsiteFinder), `geocode.py` (Nominatim, disk-cached).
- `intent/` – PPRA tenders + company-page RFQ/hiring signals.
- `qualification/buyer_classifier.py` (BUYER/VENDOR/UNKNOWN gate) + `relevance.py`.
- `llm/` – `client.py` (Groq/Gemini/Ollama, retry w/ backoff), `tasks.py` (generate_keywords,
  judge_intent, extract_requirement, classify_reply, draft_hook). All grounded; deterministic
  fallback; **off does not break the engine**.
- `scoring/scoring.py` – decomposed 0–100: review_band + rating + proximity + online_gap +
  pain_evidence. `scoring/proximity.py` – haversine tier scoring.
- `enrichment/` – contacts, email patterns/verify, phones, research brief, external signals,
  `online_presence.py` (gap audit), `places.py` (Google Places API), `hours.py` (OSM hours).
- `campaign/nl_parser.py` – NL text → CampaignConfig (deterministic + optional LLM).
- `outreach/` – sequencer, sender, reply classify, mailboxes (secondary; human-approved).
- `storage/database.py` – thin plain-SQL repo; schema is `CREATE TABLE IF NOT EXISTS` applied
  once per DSN, guarded by an advisory lock; campaigns/leads/runs/drafts/etc.
- `config/` – `schema.py` (Pydantic configs), `loader.py`, `defaults/*.yaml`, `campaigns/*.yaml`
  (the 3 shipped examples), `engine.yaml`, `discovery_taxonomy.yaml`.

**Commands (Windows; strip corrupted `/e/` PATH entries first – see §7):**
```
.venv/Scripts/python.exe -m pytest -q            # tests (DB-gated ones skip without a DB)
.venv/Scripts/python.exe scripts/golden_eval.py  # classifier accuracy vs the golden set
.venv/Scripts/python.exe -m gtm_engine.cli run <campaign_id|path.yaml> --max-companies N
cd web && npm run build                          # frontend gate (tsc + eslint)
```
`.env` (gitignored) is auto-loaded; tests are isolated from it (`isolate_credentials` fixture).
**Never launch a preview/dev server** (standing user order) – verify frontend via `tsc`/`next
build`, not by running it.

**Auth model:** Supabase JWT verified in `api/auth.py` (ES256 vs JWKS). App-wide dependency
stashes the user on `request.state`; `current_user_id` reads `sub`. `GTM_AUTH_DISABLED=1` for
local; tests use `conftest.bypass_auth`.

**Working style (do this):** verify on real data, not assumptions; the engine before the UI;
grounded LLM only (nothing invented); every result carries evidence + provenance; commit +
push each coherent slice with CI kept green; keep MEMORY.md current.

---

## 5. VERIFIED FACTS – do not re-research

**APIs (re-verified live 2026-09-26 against the real key):**
- Groq `openai/gpt-oss-20b` **still works, still free-tier** (a report claimed it left the free
  tier 2026-09-11 – false for us). Binding limit ≈ **8,000 tokens/min** (req limit ~1000/min is
  not the constraint). A judge_intent call ≈ 727 tokens (~90% reasoning).
- Gemini free flash models returned 404/503 → Groq is the default; client walks a model list.
- Hunter free = **50 credits/mo, one shared pool** (verify = 0.5 credit). `docs/API_KEYS.md`
  still wrongly says "50 searches + 100 verifications" and has no Brave spend counter – stale.
- Brave: ~$5/mo credit ≈ 1,000 searches; free plan rejects the `country` param.
- Reddit search RSS = 403 from datacenter IPs (only a spoofed UA gets 200 – refused per
  `docs/DECISIONS.md`). Google News RSS works but is anti-correlated with our ICP (90 days of
  "Khaadi" → nothing usable). Both effectively dropped.
- Overture release is auto-discovered at query time (never stale). Overpass has mirror fallback.
- WhatsApp: no legit registration-check API (Meta's `contacts` endpoint always says "valid").
  Detect via `wa.me` links (proof) then `03xx` mobile prefix (candidate). ToS-safe only.

**Google Places API impact (verified 2026-10-03, Gujranwala bakeries, 20 companies):**
Without Places: 4 buyers, 0 qualified, 0 outreach-ready (max score ~35).
With Places: 4 buyers, 2 qualified, 2 outreach-ready (max score 64). 9 API calls used.
The `review_band` component (0–30 pts) is the biggest single scoring factor and is empty without
Places data. Businesses like Imtiaz Mega (6,929 reviews, 4.4★) and Junaid Jamshed (710 reviews,
4.2★) cross the qualification threshold only with Places enrichment.
**Important `.env` format:** use `GTM_GOOGLE_PLACES_API_KEY=<key>`, not `Places API key = <key>`.

**Market data (central Karachi, OSM, 2026-09-22):** 13,294 named businesses; 23.0% mobile
(WhatsApp candidates) vs 0.2% email – i.e. phone/WhatsApp is the reachable channel in PK, email
is near-empty. 3.5% have a website *tag* (a floor, not the true rate – a missing tag ≠ no site).

---

## 6. OPEN / BLOCKED (non-code, needs the user)

- CEO sign-off on **multi-country scope** (P3) and on **E3 competitor analysis**.
- Confirm **`GTM_GROQ_API_KEY` is a GitHub Actions secret** – without it the gather-leads job
  degrades to the keyword path (never breaks, but no intent/offer-derived discovery live).
- **grydinteam Vercel (qualifyr-green):** check `NEXT_PUBLIC_SUPABASE_URL` is set. If missing,
  add it (`https://tiqcqqwblmmxyttxqljm.supabase.co`) and redeploy – it's build-time, so setting
  it alone won't fix an existing build. Without it, `supabaseConfigured` is false → no auth token
  sent → API 401s on every request (the redirect loop fix prevents infinite reloads but the app
  still can't authenticate).
- **Encryption key alignment:** if grydinteam uses a DIFFERENT encryption key than Hasee10, keys
  encrypted by one can't be decrypted by the other (same DB). Either use the same key on both, or
  migrate to separate Supabase projects.
- Missing keys: `GTM_SHEETS_CREDENTIALS_JSON`, `GTM_MAILBOX_2_*`, `GTM_GMAIL_REFRESH_TOKEN`
  (needs `gtm outreach gmail-auth`).
- `docs/API_KEYS.md` quota text is stale (Hunter/Brave); no Brave monthly spend counter in code.
- Support email in the landing FAQ is `outreach.grydin@gmail.com`.
- **Outreach end-to-end test** – mailbox UI is built, needs user to add SMTP creds and test
  sending from the Outreach tab.

---

## 7. ENVIRONMENT QUIRKS

- **PATH** has corrupted `E:\` entries (`E:\Windsurf\bin`, `E:\flutter\bin`) that break `pip`/
  `npm` – strip `/e/` from PATH first: `export PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '^/e/' | tr '\n' ':')`.
- Long bash heredocs with Python fail to parse in Git Bash – write scripts to the scratchpad.
- No local Postgres password → DB-gated tests skip locally; rely on CI (postgres service) for them.
- Overpass main endpoint rate-limits under load; mirrors work. `request_timeout_s=15` is too
  short for city-wide queries – raise per call.
- Git may warn LF→CRLF on commit; harmless.

---

## 8. HISTORICAL (superseded – kept only as a pointer)

Phases **A–G** (discover → crawl → classify → contacts → verify → score → human-approved
outreach → reply sync) are complete and are the engine's foundation; details in
`docs/ROADMAP.txt`. The **Phase-H "website-selling pivot"** (2026-09-22: sell websites to
businesses with no/dead sites, WhatsApp-first) was **superseded by the 2026-09-25 reframe** –
website-selling is now just one possible offer. The detailed Phase-H task lists and its
"WhatsApp channel / web-presence axis" plans are **obsolete**; the market data and WhatsApp-
detection facts from that work are preserved in §5. Do not treat any Phase-H task as a current
TODO – the live plan is §2–§3.
