# Contributing to Qualifyr

Thanks for your interest in contributing! Qualifyr is a B2B market-research engine
focused on Pakistan. We welcome bug reports, feature ideas, and pull requests.

## Getting started

1. **Fork** the repo and clone your fork
2. **Install Python 3.12+** and create a virtualenv:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -e ".[api,dev]"
   ```
3. **Install Node 20+** for the frontend:
   ```bash
   cd web && npm ci
   ```
4. **Copy the env example:**
   ```bash
   cp .env.example .env
   ```
   Fill in any API keys you have (all are optional; the engine degrades gracefully).

## Running tests

```bash
# Python tests (DB-gated tests skip without a local Postgres)
pytest -q

# Frontend type-check + lint
cd web && npm run build
```

CI runs the full suite with a throwaway Postgres service. Locally, ~90 DB-gated
tests will skip, which is fine for development.

## Making changes

1. Create a feature branch from `main`
2. Make your changes
3. Run `pytest -q` and `cd web && npm run build` to verify
4. Commit with a clear message describing **why**, not just what
5. Open a pull request against `main`

## Code style

- Python: follow existing patterns, no strict formatter enforced
- TypeScript/React: Tailwind + shadcn, follows Next.js conventions
- No comments unless the **why** is non-obvious
- No premature abstractions; three similar lines > one clever helper

## API keys

The engine works without any API keys (uses free fallbacks). To unlock
premium features, add your own keys in the Settings page:

| Key | What it unlocks | Free fallback |
|-----|----------------|---------------|
| Brave Search | Better web discovery | DuckDuckGo |
| Groq | LLM features (intent, keywords) | Deterministic only |
| Google Gemini | LLM fallback | Groq or deterministic |
| Hunter.io | Email verification | MX record check |
| Google Places | Ratings, reviews, hours | OSM/Overture only |

## Reporting issues

Open an issue on GitHub with:
- What you expected vs what happened
- Steps to reproduce
- Any relevant error output

## License

By contributing, you agree that your contributions will be licensed under the
Apache License 2.0.
