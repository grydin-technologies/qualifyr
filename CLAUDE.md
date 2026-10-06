# Qualifyr – B2B lead-gen / market-research engine (Pakistan-focused)

Read `MEMORY.md` (repo root) before doing anything – it has the full architecture, file map,
what's built, commands, verified facts, and open items. Do NOT explore the codebase with
glob/grep to "understand" it; MEMORY.md is kept current and has everything you need.

Read `PLAN.md` for product direction.

## Key rules

- **Plan before code** for multi-module work – write plan, get approval, then implement
- **Auto commit and push** – finish work with a push, don't hand it back
- **Grounded LLM only** – nothing invented, deterministic fallback always runs
- **Human approval before any outreach** – nothing sends unattended
- **Quality over quantity** – 3-5 excellent results = success
- **Pakistan only** for now – multi-country needs CEO sign-off
- **Never launch a preview/dev server** – verify frontend via `tsc`/`next build`
- **Google Places API key is shared** with another project – budget is 20 calls/run, never increase without asking

## Quick reference

- Engine: `gtm_engine/` (Python 3.12+, FastAPI, psycopg/Supabase)
- Frontend: `web/` (Next.js 16, Tailwind, shadcn)
- Tests: `pytest -q` (full suite ~530 tests, ~1 min in CI, ~48 min locally against remote Supabase)
- Run locally: `python -m gtm_engine.cli run <campaign_id|path.yaml> --max-companies N`
- NL campaign: `python -m gtm_engine.cli nl "find grocery stores in Islamabad"`
- Frontend check: `cd web && npm run build`
- CI: `.github/workflows/ci.yml` (test + web jobs)
- Crawl: `.github/workflows/gather-leads.yml` (weekly cron, manual dispatch)

## Scoring (decomposed, max 100)

`review_band(0-30) + rating(0-10) + proximity_tier(0-15) + online_gap(0-25) + pain_evidence(0-20)`

Routing: high_priority=55, qualified=40, review=20
