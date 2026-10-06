"""Generate bulk-import env files for Vercel and GitHub Actions.

Vercel accepts a pasted/dragged .env on its Environment Variables screen and creates
every variable at once, which beats ~18 hand-typed form fills (and makes the 2 KB
service-account private key a non-event). GitHub has the same shortcut from the CLI:
`gh secret set -f .env.github`.

The two hosts do not get the same file. They read overlapping but different sets of
keys, and GTM_DATABASE_URL in particular needs a *different port* on each (see below).

Reads .env plus sheets-api-key.json; writes .env.vercel and .env.github, all gitignored.
Run:  .venv\\Scripts\\python.exe scripts\\make_vercel_env.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# What the Vercel-hosted API function actually reads. Deliberately excludes the crawl-only
# keys (Brave/Hunter) – those are consumed by the GitHub Actions jobs, and shipping a
# secret to a host that never uses it is pure downside.
VERCEL_KEYS = [
    "GTM_DATABASE_URL",
    # Auth. GTM_SUPABASE_URL is what the API verifies bearer tokens against; without it
    # every request 500s by design. The NEXT_PUBLIC_* pair is inlined into the browser
    # bundle at build time, so Vercel needs a redeploy after these are added.
    "GTM_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
    "GTM_GITHUB_TOKEN",
    "GTM_GITHUB_REPO",
    "GTM_GITHUB_REF",
    "GTM_SHEETS_SPREADSHEET_ID",
    "GTM_GROQ_API_KEY",
    "GTM_GMAIL_CLIENT_ID",
    "GTM_GMAIL_CLIENT_SECRET",
    "GTM_GMAIL_REFRESH_TOKEN",
    "GTM_SMTP_USER",
    "GTM_SMTP_PASSWORD",
]


# What the GitHub Actions jobs read (union of gather-leads.yml and outreach.yml).
# Includes the crawl keys Vercel does not get, and excludes the dispatch token –
# Actions cannot dispatch itself.
GITHUB_KEYS = [
    "GTM_DATABASE_URL",
    "GTM_GROQ_API_KEY",
    "GTM_BRAVE_API_KEY",
    "GTM_HUNTER_API_KEY",
    "GTM_SHEETS_SPREADSHEET_ID",
    "GTM_GMAIL_CLIENT_ID",
    "GTM_GMAIL_CLIENT_SECRET",
    "GTM_GMAIL_REFRESH_TOKEN",
    "GTM_SMTP_USER",
    "GTM_SMTP_PASSWORD",
    "GTM_MAILBOX_2_USER",
    "GTM_MAILBOX_2_PASSWORD",
]


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def sheets_credentials() -> str | None:
    """The whole service account, collapsed to one line.

    The \\n inside the private key survives as the two-character escape json.dumps
    writes, which is what Google's client expects to read back.
    """
    creds = ROOT / "sheets-api-key.json"
    if not creds.exists():
        return None
    return json.dumps(json.loads(creds.read_text(encoding="utf-8")), separators=(",", ":"))


def write_target(name: str, keys: list[str], env: dict[str, str], *, transaction_pooler: bool) -> None:
    lines: list[str] = []
    missing: list[str] = []

    for key in keys:
        value = env.get(key, "")
        if not value:
            missing.append(key)
            continue
        # Supabase hands out :5432 (the session pooler), which holds one connection per
        # client. That is right for a long-lived process and fatal for serverless, where
        # every cold function grabs one and the project's limit is gone in a burst.
        # :6543 is the transaction pooler. So Vercel gets :6543, Actions keeps :5432 –
        # same database, and the wrong one fails only under load, which is the worst
        # time to find out.
        if key == "GTM_DATABASE_URL" and transaction_pooler:
            value = value.replace(".supabase.com:5432/", ".supabase.com:6543/")
        lines.append(f"{key}={value}")

    creds = sheets_credentials()
    if creds:
        lines.append(f"GTM_SHEETS_CREDENTIALS_JSON={creds}")
    else:
        missing.append("GTM_SHEETS_CREDENTIALS_JSON (sheets-api-key.json not found)")

    out = ROOT / name
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    port = ":6543 transaction pooler" if transaction_pooler else ":5432 session pooler"
    print(f"\nwrote {out} ({len(lines)} variables, DB on {port})")
    for key in keys:
        if env.get(key):
            print(f"  ok      {key}")
    if creds:
        print(f"  ok      GTM_SHEETS_CREDENTIALS_JSON ({len(creds)} chars)")
    for key in missing:
        print(f"  MISSING {key}")


def main() -> None:
    env = read_env(ROOT / ".env")
    write_target(".env.vercel", VERCEL_KEYS, env, transaction_pooler=True)
    write_target(".env.github", GITHUB_KEYS, env, transaction_pooler=False)

    print("\nMissing values are left out entirely rather than written blank – an empty")
    print("env var reads as 'configured' to both hosts and silently breaks things.")
    print("\nImport:")
    print("  Vercel  Settings -> Environment Variables -> drag .env.vercel")
    print("  GitHub  gh secret set -f .env.github   (or Settings -> Secrets, one by one)")
    print("\nNEXT_PUBLIC_API_URL is not included: set it in Vercel to")
    print("https://<your-deployment>.vercel.app/api once you know the URL.")
    print("Delete both files once imported – they are gitignored, not encrypted.")


if __name__ == "__main__":
    main()
