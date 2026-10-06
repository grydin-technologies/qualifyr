# API keys & credentials registry

Single source of truth for every external credential the engine can use. All are free
tiers. Values live only in GitHub Actions secrets (or your local environment) – never in
the repo. **Status** is updated as keys are added.

| Env var | Service | Used for | Free tier | Required? | Status |
|---|---|---|---|---|---|
| `GTM_SMTP_USER` | Gmail | Mailbox #1 address (sending + IMAP reply sync) | free account | yes (or `GTM_MAILBOX_1_USER`) | ✅ set |
| `GTM_SMTP_PASSWORD` | Gmail App Password | Mailbox #1 auth (fallback to OAuth2) | free | one of password / OAuth | ✅ set |
| `GTM_GMAIL_CLIENT_ID` / `GTM_GMAIL_CLIENT_SECRET` | Google Cloud OAuth client | Mailbox #1 OAuth2 (XOAUTH2), replaces the App Password | free | optional (preferred) | ✅ **set & tested** (client accepted by Google's token endpoint) |
| `GTM_GMAIL_REFRESH_TOKEN` | same OAuth client | Completes OAuth2 sending | free | optional | ⏳ **you must run `gtm outreach gmail-auth`** – it needs your Google sign-in |
| `GTM_MAILBOX_2_USER` / `GTM_MAILBOX_2_PASSWORD` | Gmail | Mailbox #2 for rotation | free | optional | ⏳ **no values in the PDF** (listed as requested only) |
| `GTM_MAILBOX_N_USER` / `_PASSWORD` / `_CLIENT_ID` / `_CLIENT_SECRET` / `_REFRESH_TOKEN` / `_LIMIT` / `_NAME` | Gmail | Further mailboxes (slots 3–10) | free | optional | – |
| `GTM_REACHER_URL` | Self-hosted Reacher (`check-if-email-exists`) | Mailbox-level email verification → `deliverable` status; unlocks decision-maker email confirmation | free software; needs a host with outbound port 25 | optional | ⏳ not set |
| `GTM_HUNTER_API_KEY` | Hunter.io | Mailbox-level verification, spent only on decision-maker candidates | free: **50 credits/mo, one shared pool** (a verification = 0.5 credit) | optional | ✅ **set & tested** (live: `customercare.pk@bata.com` → deliverable, score 100) |
| `GTM_BRAVE_API_KEY` | Brave Search API | Website finder + web-search discovery (E2); DuckDuckGo HTML is the keyless fallback | free: **~$5/mo credit ≈ 1,000 searches** (card required); no in-code spend counter yet | optional | ✅ **set & tested** (found khaadi.com, gulahmed.com). Note: the free plan rejects the `country` parameter |
| `GTM_GOOGLE_CSE_KEY` / `GTM_GOOGLE_CSE_ID` | Google Custom Search JSON | Website finder fallback | 100 queries/day | optional | ⏳ planned (Phase D) |
| `GTM_GROQ_API_KEY` | Groq (`openai/gpt-oss-20b`) | Optional LLM layer (`enable_llm: true`) | free, rate-limited | optional | ✅ **set & tested** (extracted a tender requirement, classified a reply) |
| `GTM_GEMINI_API_KEY` | Google Gemini | LLM fallback after Groq | free, rate-limited | optional | ⚠️ key valid, but every free flash model returned 404/503 on 2026-09-22; Groq is used instead |
| `GTM_SHEETS_SPREADSHEET_ID` | Google Sheets | Target sheet for the lead mirror | free | optional | ✅ set (id present) |
| `GTM_SHEETS_CREDENTIALS_JSON` | Google service account | Auth for the sheet mirror | free | optional | ⏳ **not supplied** – the PDF points at `sheets-api-key.json` in a Drive folder I cannot open; paste its contents as one line |
| `GTM_CORS_ORIGINS` | – | Comma-separated extra origins allowed to call the API (e.g. the deployed frontend URL); `localhost:3000` is always allowed | n/a | optional | – |
| `GTM_DATABASE_URL` | Supabase Postgres (pooler connection string) | Primary datastore, replacing local SQLite – required everywhere the engine runs (API, CLI, GitHub Actions) | free tier | **yes** | ✅ set (Supabase project provisioned) |
| `GTM_GITHUB_TOKEN` | GitHub PAT (repo-scoped, `actions:write`) | Lets the deployed API trigger `gather-leads.yml` / `outreach.yml` via `workflow_dispatch` instead of running them in-request | free | required on Vercel | ⏳ not set |
| `GTM_GITHUB_READ_TOKEN` | GitHub PAT (no scopes needed) | Raises the GitHub REST rate limit for org-activity signals (`gtm_engine/enrichment/github_signals.py`) from 60/hr to 5000/hr. **Deliberately separate from `GTM_GITHUB_TOKEN`** – that one has `actions:write` and has no business being handed to a job that only reads third-party orgs. Falls back to `GTM_GITHUB_TOKEN` if unset, so this is a hardening step, not a breaking change | free | optional (works keyless, just rate-limited) | ⏳ not set |
| `GTM_GITHUB_REPO` | – | `owner/repo` for the dispatch call above | n/a | required on Vercel | ⏳ not set |
| `GTM_GITHUB_REF` | – | Branch to run the dispatched workflow from; defaults to `main` | n/a | optional | – |
| `GTM_SUPABASE_URL` | Supabase (same project as the database) | Where the API fetches the public JWKS to verify bearer tokens. Every route except `/health` needs one. Not a secret – it is a hostname. Unset means every request 500s **on purpose**: an unset variable must never reopen the API | free | **yes, wherever the API runs** | ⏳ not set |
| `GTM_AUTH_DISABLED` | – | Local dev only: skips the token check. An opt-*out*, so a typo leaves auth on. Never set this on a deployment | n/a | optional | – |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase | Frontend sign-in. Belongs in `web/.env.local` and in Vercel, not in the root `.env` | free | **yes on Vercel** | ⏳ not set |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase | Publishable key, designed to sit in a browser bundle. Inlined at **build** time, so it needs a redeploy to take effect | free | **yes on Vercel** | ⏳ not set |

Note: Supabase's **service-role/anon API keys are not used** by this engine – storage
goes over plain SQL via `psycopg` against `GTM_DATABASE_URL`, not the Supabase REST/client
API. Keep them out of Vercel/Actions unless something starts calling that API directly.

## Keyless services in use

Overture Maps (S3 parquet), OpenStreetMap Overpass + mirrors, Nominatim, GDELT news (rate-limited),
RDAP domain age (not for .pk), KCCI member directory (scraped, cached weekly), Google Fonts (UI).

## Where they are read

- Mailboxes: `gtm_engine/outreach/mailboxes.py` (`load_mailboxes`)
- Gmail OAuth: `gtm_engine/outreach/gmail_oauth.py`
- Verifiers: `gtm_engine/validation/verifier.py` (`build_verifier`)
- Workflows pass them through: `.github/workflows/outreach.yml`, `verify-sent.yml`

## Local use

`.env` in the project root is loaded automatically at start-up (and is gitignored). Real
environment variables always win, so CI secrets are never overridden by a stale file. Tests
are isolated from it deliberately – a developer's live key must not change which code path runs.

## Adding a key

1. GitHub → Settings → Secrets and variables → Actions → *New repository secret*.
2. Add the same name to the `env:` block of the relevant workflow if it is new.
3. Update the **Status** column here.
