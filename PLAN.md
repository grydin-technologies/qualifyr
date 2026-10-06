# Qualifyr – Product Plan

The direction of record for where the product is going. Captured from the founder's
2026-09-25 brief. Supersedes the working assumptions in the current build where they
conflict. `docs/DIRECTION.md` (CEO) and `MEMORY.md` remain the other standing references.

---

## What this is – and what it is not

**Qualifyr is a market-research search engine, not a lead-generation / cold-email tool.**
The engine is the product. You describe what you offer (or who you compete with); it
searches real companies from free public sources, researches each one deeply, and returns a
**small set of strictly-relevant results** with the evidence and the decision-maker behind
each. Campaigns and outreach are secondary conveniences layered on top – not the point.

It exists to answer two questions:

1. **Market search – "where can we sell this?"** You describe your solution; the engine
   finds companies that plausibly need it, with the evidence (hiring, intent, pain) and the
   people to talk to. The pitch it enables: *"you have these problems, here's what we've
   solved for companies like yours."*
2. **Competitor analysis – "what are my competitors doing?"** You describe your product; the
   engine finds your competitors and surfaces what they are doing – hiring, investing,
   expanding, launching – as signal you can act on.

It is **not** a bulk email blaster, not a generic contact database, not quantity-driven.
**3–5 excellent, defensible results beat 500 shallow ones.** This is for research, not spray.

The whole thing must **deviate from a conventional lead-generation tool** – the value is the
search and the research quality, not "here's an email, now cold-outreach everyone."

---

## Priorities (in the founder's stated order)

### P1 – Dynamic campaigns
**Today:** three hardcoded campaign YAML files (`config/campaigns/`). Adding one needs a code
edit and a deploy.

**Target:** a user creates a campaign from input – a form in Settings (or a dedicated "New
search" screen) – and the engine generates leads for it. Any campaign can be **run multiple
times**, and **old and new results are both kept** (runs accumulate; nothing is overwritten).

Scope:
- A campaign-creation form: name, what you offer, region (see P3), target terms, result cap.
- Persist campaigns as **rows in the DB**, editable at runtime – not files on disk. (A
  `campaigns` table already exists in `gtm_engine/storage/database.py`; it is currently a
  mirror of the YAML, not the source of truth.)
- Runs are append-only and browsable per campaign; history is preserved.
- Touches: `gtm_engine/api/main.py` (campaign CRUD), the web Settings/Campaigns pages,
  `gather-leads.yml` (already parameterised by campaign), the campaign loader.

### P2 – Hard filters + LLM-generated keywords (strict relevance)
**The Imtiaz problem:** "Imtiaz Mega, Gulberg Greens" was tagged because it was hiring – but
Imtiaz is a large retailer that sells plenty itself, and we don't know whether it was hiring
someone **relevant to us** or just a salesman for its own floor. **A signal without relevance
is noise.** The strict qualification bar from the original proposal is missing and must come
back – nothing short of what the proposal specified.

**Target:**
- The **LLM generates the search and relevance keywords dynamically** from the user's
  description of what they offer. The description is **no longer hardcoded** – the AI derives
  the keyword set, and companies are searched and matched on that basis.
- Every candidate is matched **strictly** against those keywords. Hiring / intent must be
  **text-relevant to the user's offer**, not merely "they are hiring something." A hire that
  is not relevant to what the user sells does not qualify the company.
- **Hard filters** enforce the proposal's bar before any company is returned.
- Whether a company is genuinely a buyer, and worth selling to, is **our** decision –
  surfaced with evidence for the user to judge, never asserted blindly.
- The strictness is set by what the user entered **before** running: results must be
  strictly text-relevant to those settings.
- Touches: `gtm_engine/llm/tasks.py` (keyword generation, kept grounded),
  `gtm_engine/qualification/buyer_classifier.py` (relevance gate), `gtm_engine/intent/`
  (hiring/tender relevance must be scored against the generated keywords, not accepted on
  presence alone).

### P3 – Region filter (multi-geography)
**Today:** effectively a single city (Islamabad).

**Target:** the user chooses the scope – **countries, provinces/states, cities** – and the
search runs across the chosen region. Not locked to one city.

- Touches: `geography` in the campaign config, `gtm_engine/discovery/` (OSM / Overture /
  Nominatim are already region-capable; the gate is the config and UI, not the sources).
- **Flag:** this expands beyond the earlier **"Pakistan only"** directive in
  `docs/DIRECTION.md` / `[[gtm-ceo-direction]]`. Confirm with the CEO before treating
  multi-country as approved scope.

### P4 – Result caps (API-usage control)
A **per-run cap** the user picks. Deep research on a small, capped set rather than shallow
research on many – and it directly bounds spend on the metered APIs (Brave search, Hunter
verification, the LLM). Quality per company is the point; the cap protects both quality and
cost.

### P5 – Research depth + personal details
For each returned company: the relevant **hiring, investment, expansion** signals (strictly
filtered per P2) **and** the decision-maker's **personal details**. The depth and accuracy of
the per-company research is the differentiator – this is what makes it a research tool, not a
list.

---

## Deferred – after P1–P5

### Multi-tenant personalisation (auth-scoped data) – ✅ built 2026-09-26
Sign-in now authenticates *data*. Campaigns carry an `owner_id` (the Supabase token's `sub`),
set on create and preserved across pipeline re-upserts. Campaign- and lead-scoped routes are
guarded so one account never sees another's campaigns or leads (refused as 404, not 403, so
existence is not leaked). File-based example campaigns and legacy NULL-owner campaigns stay
shared; with auth off (local operator) there is no scoping. See `require_campaign_access` /
`require_lead_access` in `gtm_engine/api/main.py` and `tests/test_multitenancy.py`.

---

## How this relates to earlier plans

- **Supersedes** the hardcoded-campaign assumption in the current build (P1).
- The **website-selling pivot** (Phase H in `MEMORY.md`) becomes **one possible "offer"** a
  user can describe – not the whole product. The engine is now **offer-agnostic**, driven by
  what the user enters, and works the same whether the offer is websites, inventory software,
  or anything else.
- **Keeps and sharpens** the CEO's **quality-over-quantity** rule – reinforced hard here
  (3–5 great results is success).
- **Elevates the LLM** from an optional enrichment layer to the thing that **generates the
  keyword/relevance model** – still grounded, still with a deterministic fallback.
- The **region filter (P3)** is the one open tension with "Pakistan only" – needs CEO sign-off.

---

## Guardrails carried forward (do not regress)

- **Grounded LLM only.** Generated keywords and relevance judgements are justified by
  observed text; nothing is invented. A deterministic path still runs without the LLM.
- **Evidence + provenance on every result** – why it matched, where each field came from.
- **Buyer / vendor / relevance gate** stays; strictness increases (P2), never loosens.
- **Human approval before any outreach.** Outreach remains secondary and opt-in.
- **Reviewer-accuracy metric** (target ≥ 80%) is how we measure whether the relevance work
  is actually working.

---

## Suggested build order

1. **P1 dynamic campaigns** – unblocks everything; without runtime campaigns the rest can't
   be exercised by a real user.
2. **P3 region filter** – small, and P2's research runs against whatever region P1 sets.
3. **P2 hard filters + LLM keywords** – the core quality work; the reason the tool is
   different. Needs a golden set to prove relevance improved (see `MEMORY.md`).
4. **P4 caps** – a small addition once P1–P2 exist.
5. **P5 depth** – layered onto the qualified set.
6. **Multi-tenancy** – last, as the founder specified.
