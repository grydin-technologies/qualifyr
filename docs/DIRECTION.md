# Product direction (CEO notes, 2026-09-21)

These override earlier assumptions where they conflict. Every phase is judged against them.

## Principles

1. **Pakistan only.** We know the market and can verify lead quality ourselves. No GCC, no
   "cover the world". Geography stays configurable but the product, sources and copy are
   built for Pakistan (SECP, chambers, `.pk`, `03xx` mobiles, Urdu-script pages).
2. **Quality over quantity – by a wide margin.** 1, 2 or 5 genuinely qualified leads per
   batch is a success. Volume is not a metric. The narrative we market is *"few, highly
   qualified, explainable leads"*, so anything that inflates counts at the cost of
   confidence is wrong.
3. **Core things done properly, not everything.** Small surface, deep verification.
4. **Open source, collaboration-ready.** Clean module boundaries, config over code,
   tests per module, docs that let a stranger add a source or a rule.
5. **Scalable architecture.** Adapters (`DiscoverySource`, `Fetcher`, `Sender`) and
   config-driven rules so growth is adding modules, not rewriting.

## Three capabilities the CEO asked for

| Ask | What it means here | Where it lands |
|---|---|---|
| **Intent & requirement scraping** | Find companies that have *expressed* a need – tenders/RFQs, job posts for roles implying a purchase, "looking for supplier/vendor" posts, expansion announcements – not just companies that exist. Each signal carries a source URL and date. | Phase D (signals & sources) → extended into Phase G |
| **LLM usage** | Approved. Used as an *optional* layer with a free/local backend (Ollama locally; free-tier hosted as fallback) for: extracting requirements from unstructured text, classifying replies, drafting personalisation from *observed* facts. Deterministic path stays the default and the fallback; LLM output is labelled, never silently trusted, and never invents facts. | Phase G |
| **Decision-maker emails** | A named owner/CEO/procurement lead with a *verified* personal mailbox, not `info@`. Pattern candidates (first.last@, first@) are only accepted when SMTP verification (Reacher) confirms the mailbox; guessed-but-unverified never ships. | Phase B (verification) → Phase G (discovery) |

## Success metric

Per batch: number of leads a human reviewer marks "correct buyer, correct person, correct
email" ÷ leads shown. Target ≥ 80%. Tracked from the approval queue (approve / reject).

## Non-goals reaffirmed

Mass volume, LinkedIn automation, paid data, tracking pixels, full CRM.
