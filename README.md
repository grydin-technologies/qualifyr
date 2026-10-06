# Qualifyr

**Describe what you sell. Qualifyr finds the companies that actually need it.**

Qualifyr is an offer-driven market-research and lead-discovery engine for Pakistan. You give it
a plain-English description of your product or service; it works out *who would buy it*, finds
real companies from free public sources (maps, chambers of commerce, government tenders, the
open web), reads each company's website, judges whether they're a genuine buyer, finds a
decision-maker and a validated email, scores every match 0–100 with a readable reason, and
returns a small set of strongly-relevant results – not a dump of thousands.

Quality over quantity is the whole point: 3–5 excellent, well-explained matches beat a spray of
unqualified contacts. Vendors, agencies, and competitors are filtered out of your results, not
mixed in. An optional outreach flow drafts emails for each match, but **nothing is ever sent
without a human approving it first.**

- **Python 3.12+** engine · **FastAPI** API · **Postgres** (Supabase) · **Next.js 16** web app
- Runs on a laptop, in **GitHub Actions** (scheduled crawls + manual sends), and on **Vercel**
- Uses **free-tier public data and APIs** by default; every paid key is optional

> Built and tested for the **Pakistan** market (local chambers, PPRA tenders, city/sector
> geography). The pipeline is country-agnostic, but the defaults and data sources are PK-first.

---

## Table of contents

1. [What it does](#what-it-does)
2. [How a result is produced](#how-a-result-is-produced)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
   - [1. Clone and install the engine](#1-clone-and-install-the-engine)
   - [2. Create the database (Supabase)](#2-create-the-database-supabase)
   - [3. Configure environment variables](#3-configure-environment-variables)
   - [4. (Optional) Set up the web app](#4-optional-set-up-the-web-app)
5. [Running it](#running-it)
6. [Configuration](#configuration)
7. [API keys – what each one unlocks](#api-keys--what-each-one-unlocks)
8. [The web app](#the-web-app)
9. [Outreach (approval-gated)](#outreach-approval-gated)
10. [Deployment](#deployment)
11. [Project layout](#project-layout)
12. [Testing](#testing)
13. [Troubleshooting](#troubleshooting)
14. [Contributing & license](#contributing--license)

---

## What it does

- **Offer → targets.** You describe what you sell. A curated taxonomy (plus an optional LLM)
  turns that into the map categories and search queries most likely to contain buyers – so you
  don't need to know OpenStreetMap tag syntax.
- **Discovery from free sources.** OpenStreetMap/Overpass, Overture Maps, the KCCI member
  directory, PPRA government tenders, keyless/Brave web search, and seed CSVs.
- **Real qualification, with evidence.** Each company's site is crawled and classified
  **BUYER / VENDOR / UNKNOWN**; an optional grounded LLM judges *intent* (does this company
  actually need the offer?). Every verdict carries the evidence it was based on.
- **Decision-maker + validated email.** Finds a named contact and their email, checks syntax and
  MX, and (optionally) verifies deliverability.
- **Transparent scoring.** 0–100 from five components – review band, rating, proximity, online
  gap, and pain evidence – each with a plain-language reason.
- **Clean output.** A client-ready CSV, a per-company research brief, and a web dashboard.
- **Human-approved outreach.** A 3-step email sequence that only sends after you approve each
  draft, with sender protection (warm-up, spacing, bounce guard) and reply/bounce/STOP handling.

---

## How a result is produced

```
describe offer ─► derive targets (taxonomy + optional LLM)
   │
   ▼
discover (Overture · OSM · KCCI · PPRA · web search · seed CSV)
   ─► dedupe (domain, name+city) ─► relevance filter (offer keywords + LLM type check)
   ─► find website (search fallback) ─► check the domain is still live
   ─► crawl ≤ N pages ─► classify BUYER / VENDOR / UNKNOWN ─► judge intent (LLM)
   ─► contacts + buying/pain signals ─► email syntax + MX ─► decision-maker email + verify
   ─► enrich (Google Places rating/reviews, opening hours, online-presence gap)
   ─► score 0–100 with reasons ─► store ─► CSV + research brief
```

Every stage is driven by YAML config (see [Configuration](#configuration)); no code change is
needed to run a different search.

---

## Prerequisites

| Requirement | Why | Notes |
|---|---|---|
| **Python 3.12+** | the engine, CLI, and API | `python --version` |
| **A Supabase project** (free tier) | Postgres storage + user auth | [supabase.com](https://supabase.com) – the only hard external dependency |
| **Node.js 20+** | the web app (optional) | only if you want the UI; the CLI works without it |
| **Git** | clone + (for scheduled runs) GitHub Actions | |

Everything else – mail sending, LLM, web search, email verification, Google Places – is
**optional**. Qualifyr degrades gracefully: a missing key disables that one feature and never
breaks a run. See [API keys](#api-keys--what-each-one-unlocks).

---

## Setup

### 1. Clone and install the engine

```bash
git clone https://github.com/Hasee10/qualifyr.git
cd qualifyr

python -m venv .venv
# activate it:
#   Linux / macOS:  source .venv/bin/activate
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (Git Bash):    source .venv/Scripts/activate

pip install -e ".[api,overture]"
```

Installing with `-e` (editable) puts a `gtm` command on your PATH. Optional extras:

| Extra | Adds | Install when |
|---|---|---|
| `api` | FastAPI + uvicorn + JWT verification | you want the API / web app |
| `overture` | DuckDB (Overture Maps discovery) | recommended – a major free data source |
| `browser` | Playwright (renders JS-only sites) | sites that don't work without JS |
| `sheets` | Google Sheets export | you mirror leads to a Sheet |
| `dev` | pytest + test deps | you run the test suite |

Full local setup: `pip install -e ".[api,overture,browser,sheets,dev]"`
(then `playwright install chromium` if you added `browser`).

### 2. Create the database (Supabase)

1. Create a free project at [supabase.com](https://supabase.com).
2. **Connection string** → Project Settings → Database → *Connection string* → **Transaction
   pooler** mode. Copy it and fill in your database password. This is `GTM_DATABASE_URL`.
3. **Auth** (only needed for the web app) → the project URL (`https://xxxx.supabase.co`) is
   `GTM_SUPABASE_URL`, and the **anon/publishable** key is `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
   Enable the Email provider under Authentication → Providers.

You do **not** need to create any tables – the schema is created automatically on first
connection (`CREATE TABLE IF NOT EXISTS …`). Only the plain Postgres connection string is used;
Supabase's service-role/REST keys are not.

### 3. Configure environment variables

```bash
cp .env.example .env
```

The bare minimum to run a campaign locally:

```bash
# .env
GTM_DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-region.pooler.supabase.com:6543/postgres
GTM_AUTH_DISABLED=1          # local only – skips the API token check
```

That's enough to discover and qualify companies and export a CSV. `.env` is auto-loaded and is
gitignored – never commit it. Add optional keys as you need the features behind them
([table below](#api-keys--what-each-one-unlocks)); `.env.example` documents every variable.

### 4. (Optional) Set up the web app

```bash
cd web
npm install
```

Create `web/.env.local`:

```bash
# web/.env.local
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=http://localhost:8000     # where the FastAPI server runs
```

These are **publishable** and inlined into the browser bundle (the anon key is designed for
that). On Vercel they're baked in at build time, so changing them needs a redeploy.

---

## Running it

The `gtm` command (from the editable install) is cross-platform. If it isn't on your PATH, use
`python -m gtm_engine.cli …` instead.

**Run a campaign end-to-end** (discover → qualify → score → CSV):

```bash
gtm run config/campaigns/example_retail_islamabad.yaml --max-companies 20
```

Outputs land in `data/exports/<campaign>_<timestamp>_<run>_qualified.csv` (matches ≥ min_score)
and `..._all.csv` (everything, for audit).

**Create a campaign from plain English** (needs a Groq key for best results, works without one):

```bash
gtm nl "find grocery stores in Islamabad that need inventory software"
```

**Other CLI commands:**

```bash
gtm export <campaign_id> --min-score 70        # re-export stored leads
gtm runs                                        # list past runs
gtm campaign-id <path-or-id>                    # resolve a campaign id
gtm suppress someone@company.pk --reason "..."  # never contact again
gtm sheets <campaign_id>                         # mirror to Google Sheets (needs creds)
```

**Run the API** (needed for the web app):

```bash
uvicorn gtm_engine.api.main:app --reload        # http://localhost:8000
```

**Run the web app** (in another terminal):

```bash
cd web && npm run dev                            # http://localhost:3000
```

Open `http://localhost:3000`, sign up, and create a campaign from the UI.

---

## Configuration

Campaigns are YAML. Three worked examples live in `config/campaigns/`. A campaign defines the
offer, geography, and thresholds; the engine derives discovery targets from the offer, but you
can override categories/queries explicitly.

| File | Controls |
|---|---|
| `config/campaigns/*.yaml` | offer, industries, cities/areas, keywords, OSM/Overture categories, min score, max companies |
| `config/defaults/discovery_taxonomy.yaml` | offer → sector → map categories (how an offer becomes a search) |
| `config/defaults/vendor_rules.yaml` | negative keywords + vendor self-description phrases (the buyer gate) |
| `config/defaults/roles.yaml` | decision-maker role whitelist, sell-side blacklist, generic mailboxes |
| `config/defaults/signals.yaml` · `intent.yaml` | buying/pain signal phrases; tender/RFQ/hiring intent phrases |
| `config/engine.yaml` | concurrency, timeouts, rate limits, robots, LLM provider, scoring toggles |
| `config/outreach/settings.yaml` · `templates.yaml` | send window, caps, spacing; email copy |

Most `engine.yaml` settings can be overridden by `GTM_*` environment variables.

**Scoring** (max 100): `review_band(0–30) + rating(0–10) + proximity_tier(0–15) +
online_gap(0–25) + pain_evidence(0–20)`. Routing thresholds: high-priority 55, qualified 40,
review 20.

---

## API keys – what each one unlocks

All optional. A missing key disables only that feature. Full details and current quotas live in
[`docs/API_KEYS.md`](docs/API_KEYS.md).

| Key(s) | Unlocks | Free tier |
|---|---|---|
| `GTM_GROQ_API_KEY` | LLM layer: offer→targets, intent judging, relevance, query generation | Groq `gpt-oss-20b`, ~8k tokens/min |
| `GTM_BRAVE_API_KEY` | web-search discovery + website finding (falls back to keyless DuckDuckGo) | ~1k searches/mo (card required) |
| `GTM_GOOGLE_PLACES_API_KEY` | rating, review count, hours, review text (biggest scoring boost) | ~1k calls/mo |
| `GTM_HUNTER_API_KEY` / `GTM_REACHER_URL` | decision-maker email verification | Hunter free; Reacher self-host |
| `GTM_SMTP_*` / `GTM_GMAIL_*` | actually sending outreach (otherwise every send is a dry run) | – |
| `GTM_SHEETS_*` | Google Sheets export mirror | – |
| `GTM_GEMINI_API_KEY` | alternate LLM (Groq is the reliable default) | often 404/503 on free tier |

**Per-user keys (self-hosting):** in the web app, each user stores their own keys (encrypted at
rest with `GTM_ENCRYPTION_KEY`), with per-day usage limits and a free tier (3 campaigns, 10
leads each). Generate the encryption key once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## The web app

Five pages (`web/`, Next.js 16 + Tailwind + shadcn):

- **Dashboard** – counts, score distribution, top matches, campaign meta.
- **Campaigns** – create a search (plain-English or manual), run discovery with live progress,
  download CSV, edit/delete.
- **Leads** – every company processed, newest first; filter by type/score, search, open a lead
  to see every reason, the research brief, and its activity; suppress.
- **Outreach** – the approval queue: each due email is rendered, you edit subject/body, approve
  or reject, then send; plus in-sequence and activity views.
- **Settings** – API keys, usage limits, mailboxes.

---

## Outreach (approval-gated)

Nothing is sent unattended. Each due email is drafted from a template, shown in the UI, editable,
and sent only after you approve it. Follow-ups come back for their own approval.

```bash
gtm outreach preview <campaign_id>              # see the drafted emails
gtm outreach send <campaign_id> --dry-run       # writes .eml files to data/outbox/
gtm outreach send <campaign_id>                 # real send (needs mail credentials)
gtm outreach status <campaign_id>
```

**Sequence:** Email 1 → +3 days Follow-up 1 → +4 days Follow-up 2, threaded; stops on reply,
bounce, "STOP", or suppression. **Sender protection** is on by default: warm-up ramp, 30–120s
random spacing, a 09:00–18:00 Asia/Karachi weekday window, and a bounce-rate guard. Several
mailboxes rotate (`GTM_MAILBOX_1_*` … `_10_*`); Email 1 goes to the least-loaded mailbox,
follow-ups stay on the thread's mailbox. Replies are pulled over IMAP and classified. Every send
is recorded in a durable ledger so an address never gets the same step twice.

Preferred credentials: Gmail OAuth2 – set `GTM_GMAIL_CLIENT_ID/SECRET` + `GTM_SMTP_USER` and run
`gtm outreach gmail-auth` once. Fallback: `GTM_SMTP_PASSWORD` (an App Password).

---

## Deployment

The production topology (how the hosted alpha runs):

- **Web app + API → Vercel.** The API is a Python function (`web/api/index.py`);
  `web/vercel.json` bundles `gtm_engine/` + `config/` and rewrites `/api/*` to it.
- **Database → Supabase** (`GTM_DATABASE_URL`, `GTM_SUPABASE_URL`).
- **Long jobs → GitHub Actions.** The deployed API is treated as read-only for crawling/sending;
  it *dispatches* workflows (`GTM_GITHUB_TOKEN`, `GTM_GITHUB_REPO`) rather than crawling
  in-request, because runs take minutes-to-hours.

Workflows (`.github/workflows/`):

| Workflow | Trigger | Does |
|---|---|---|
| `gather-leads.yml` | weekly cron + manual | discovery/crawl, commits leads (never contacts anyone) |
| `outreach.yml` | **manual only, by design** | sends approved emails (no cron – nothing emails unattended) |
| `verify-sent.yml` | post-send | delivery verification |
| `ci.yml` | push/PR | tests + web build |
| `pages.yml` | push | GitHub Pages landing page |

Set `GTM_CORS_ORIGINS` to your deployed frontend origin (`localhost:3000` is always allowed).
CORS is a browser policy, not access control – the Supabase bearer-token check protects the data.

---

## Project layout

```
gtm_engine/
  config/         pydantic schema + YAML loader + defaults
  discovery/      targeting.py (offer→targets), overture.py, osm.py, chambers.py (KCCI),
                  web_search.py, geocode.py (Nominatim), csv_seed.py, search.py (website finder)
  scraping/       fetcher.py (polite HTTP), integrity.py (parked/soft-404), browser.py (Playwright),
                  site_crawler.py, parsers.py
  qualification/  buyer_classifier.py (the gate) + relevance.py
  intent/         ppra.py (PK tenders), company_pages.py (RFQ/hiring signals)
  enrichment/     contacts, signals, email_patterns, places.py (Google Places), online_presence.py,
                  hours.py, research.py (research brief), fieldclean.py
  llm/            client.py (Groq/Gemini/Ollama) + tasks.py – grounded, optional, off by default
  scoring/        scoring.py (decomposed 0–100) + proximity.py
  validation/     domains, emails, dedupe, verifier (Hunter/Reacher/MX), liveness
  outreach/       sequencer, sender, reply classifier, mailboxes, durable ledger
  export/         csv_export.py, sheets.py
  storage/        database.py (Postgres via psycopg, plain SQL, no ORM)
  api/            FastAPI backend (also the Vercel function)
  pipeline.py     orchestration · cli.py
web/              Next.js 16 app (web/README.md for its own notes)
config/           campaigns, defaults, engine.yaml, outreach settings
tests/            pytest suite (HTML/Overpass fixtures, disposable Postgres schema per run)
docs/             API_KEYS.md, DECISIONS.md, DIRECTION.md, REQUIREMENTS.md, ROADMAP.txt
.github/workflows/
```

---

## Testing

```bash
pytest -q
```

Tests that need a database are skipped unless `GTM_TEST_DATABASE_URL` (or `GTM_DATABASE_URL`) is
set; they create and drop a throwaway schema per run, so they never touch real data. CI runs the
full suite against a disposable Postgres service, plus the web build.

```bash
# frontend checks
cd web && npm run build          # tsc + eslint + production build
```

---

## Troubleshooting

- **Every API request returns 500.** `GTM_SUPABASE_URL` is unset. This is deliberate – an unset
  auth variable must never silently open the API. Set it, or use `GTM_AUTH_DISABLED=1` locally.
- **DB-backed tests all skip.** Expected without `GTM_TEST_DATABASE_URL` / `GTM_DATABASE_URL`.
- **No companies discovered.** With no Brave key and no explicit categories, give the offer more
  signal, or add OSM categories / search queries in the campaign; install the `overture` extra
  for the Overture data source.
- **Sends do nothing.** With no mail credentials every send is a dry run (writes `.eml` files to
  `data/outbox/`). Add `GTM_GMAIL_*` or `GTM_SMTP_*`.
- **Sign-up says sign-up isn't configured.** `NEXT_PUBLIC_SUPABASE_URL` / `_ANON_KEY` are missing
  from the build – on Vercel, add them and redeploy (they're inlined at build time).

---

## Contributing & license

Issues and PRs welcome. Before opening a PR: `pytest -q` and `cd web && npm run build` should
both pass. See `docs/DECISIONS.md` for *why* things are built the way they are, and
`docs/API_KEYS.md` for the full credential registry.

> **License:** add a `LICENSE` file before publishing (e.g. MIT or Apache-2.0). This repo does
> not yet declare one.
