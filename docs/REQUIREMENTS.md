# Requirements – GTM Lead Engine (Phase 1)

Consolidated from the two source specs (`GTM_Lead_Engine_Claude_Code_Spec.docx` is primary;
`GTM_Lead_Engine_Spec_Claude_Code.docx` contributed the role whitelist/blacklist and Brevo as
an SMTP option). Items from the older spec that conflict with the primary one – LinkedIn
scrapers, theHarvester, Apollo/Clay tiers – are deliberately excluded.

## Goal

A local-first, free-stack engine that finds **buyer** companies (not vendors/agencies), proves
buyer fit from public web data, identifies a decision-maker, scores each lead 0–100 with a
readable reason, and exports a clean CSV. Approved leads may enter a small, controlled email
sequence. Quality over volume: ~50–100 strong leads per batch.

Primary markets: Pakistan (Islamabad/Rawalpindi, Lahore, Karachi, Faisalabad, Multan, Peshawar),
then UAE, Saudi Arabia, Qatar, Oman. Geography is configuration, never code.

## Users

Founder / GTM operator running campaigns for their own offer. Single-tenant in Phase 1.

## Pipeline (required flow)

1. Offer / ICP configuration (YAML)
2. Buyer-oriented source discovery (OpenStreetMap/Overpass primary, seed CSV, search fallback)
3. Company website scraping (home, about, contact, team, services, careers – max N pages)
4. **Buyer / VENDOR / UNKNOWN gate** – mandatory, explainable
5. Deduplication (domain first, name+city second) + validation
6. Decision-maker discovery from public company pages only
7. Email validation (syntax + MX; no paid API; never "verified" by `@` alone)
8. Deterministic scoring: ICP fit 50 · company quality 15 · buyer evidence 15 · contact quality 10 · buying signals 10
9. CSV export (fixed 35-column schema)
10. Outreach queue → Email 1 → Follow-up 1 → Follow-up 2; stop on reply/bounce/unsubscribe/suppression
11. Reply / status tracking

## Hard rules

- VENDOR is rejected regardless of score unless the campaign explicitly allows that vendor type.
- UNKNOWN never enters outreach.
- Outreach only for `company_type=BUYER`, `score ≥ min_score`, usable validated email.
- No paid API as a required dependency. No LinkedIn automation. No CAPTCHA/auth bypass.
- Static HTTP first; browser rendering only as a fallback.
- Respect robots.txt on websites, rate limits everywhere.
- Never fabricate personalization facts.
- One lead per company per campaign unless multiple contacts are explicitly allowed.

## Routing thresholds (default)

| Score | Priority |
|-------|----------|
| 80–100 | high_priority |
| 70–79 | qualified / outreach-ready |
| 50–69 | review / enrich |
| < 50 | reject |

## Acceptance test (Phase 1)

Given "retail/ecommerce buyer companies in Islamabad/Rawalpindi": discover a batch, drop
vendors, enrich, score with reasons, show only qualified buyers, export CSV. No agencies in the
qualified output, no duplicate domains, every lead has source evidence + score reason, CSV opens
without manual cleanup, outreach never fires for UNKNOWN/rejected, runs locally with no paid data.

## Non-goals (Phase 1)

Millions of contacts, full CRM, LinkedIn dependency, paid enrichment, ML scoring, AI-generated
facts, guessed emails treated as verified, CAPTCHA bypass, high-volume cold email.

## Open questions

- Exact ICP for the first real campaign (industry, company size range, title nuances).
- Sender: Gmail/Microsoft OAuth vs Brevo SMTP free plan (300/day).
- UI template (to be provided).
