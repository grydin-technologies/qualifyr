"""One-way export of leads to a Google Sheet (free, Sheets API v4, service account).

Setup (once, free): create a service account in Google Cloud, enable the Google Sheets API,
download its JSON key, share the target spreadsheet with the service-account email
(Editor). Then set GTM_SHEETS_CREDENTIALS_JSON (the key file's contents) and
GTM_SHEETS_SPREADSHEET_ID (from the sheet URL). The sheet is a mirror for people who
will not open the UI; the database stays the source of truth."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Iterable

import httpx

from gtm_engine.export.csv_export import lead_row
from gtm_engine.models import CSV_COLUMNS, Lead

log = logging.getLogger(__name__)

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
EXTRA_COLUMNS = ["reply_label", "phone_type", "candidate_email", "domain_age_years", "mailbox"]


def configured() -> bool:
    return bool(os.environ.get("GTM_SHEETS_CREDENTIALS_JSON") and os.environ.get("GTM_SHEETS_SPREADSHEET_ID"))


def access_token() -> str:
    """Service-account bearer token via google-auth (optional extra `sheets`).

    Turns the three ways this fails into one clear, actionable message each, instead of a raw
    google-auth traceback: unparseable JSON, a key missing required fields, and – the common
    one – Google rejecting the identity ("invalid_grant: account not found"), which means the
    service account was deleted or the key is stale and must be recreated."""
    try:
        info = json.loads(os.environ["GTM_SHEETS_CREDENTIALS_JSON"])
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GTM_SHEETS_CREDENTIALS_JSON is not valid JSON – paste the service-account key "
            "file's full contents into the secret."
        ) from exc

    from google.oauth2 import service_account  # imported lazily: optional dependency
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError

    try:
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except ValueError as exc:
        raise RuntimeError(
            f"GTM_SHEETS_CREDENTIALS_JSON is missing required service-account fields: {exc}"
        ) from exc
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        email = info.get("client_email", "<unknown>")
        project = info.get("project_id", "<unknown>")
        raise RuntimeError(
            f"Google rejected the Sheets service account '{email}' (project '{project}'): "
            f"{exc.args[0] if exc.args else exc}. The key is stale or the account was deleted. "
            "Recreate the service account and a JSON key in Google Cloud, enable the Google "
            "Sheets API, share the spreadsheet with that email as Editor, then update the "
            "GTM_SHEETS_CREDENTIALS_JSON secret."
        ) from exc
    return creds.token


def rows_for(leads: Iterable[Lead]) -> list[list[str]]:
    header = CSV_COLUMNS + EXTRA_COLUMNS
    out = [header]
    for l in leads:
        base = lead_row(l)
        extra = {"reply_label": l.reply_label or "", "phone_type": l.phone_type or "",
                 "candidate_email": l.candidate_email or "",
                 "domain_age_years": "" if l.domain_age_years is None else str(l.domain_age_years),
                 "mailbox": l.mailbox or ""}
        out.append([base[c] for c in CSV_COLUMNS] + [extra[c] for c in EXTRA_COLUMNS])
    return out


class SheetsExporter:
    def __init__(self, spreadsheet_id: str, token: str, client: httpx.Client | None = None):
        self.spreadsheet_id = spreadsheet_id
        self._client = client or httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"})

    def _ensure_tab(self, title: str) -> None:
        meta = self._client.get(f"{SHEETS_API}/{self.spreadsheet_id}?fields=sheets.properties.title")
        meta.raise_for_status()
        titles = {s["properties"]["title"] for s in meta.json().get("sheets", [])}
        if title not in titles:
            r = self._client.post(f"{SHEETS_API}/{self.spreadsheet_id}:batchUpdate",
                                  json={"requests": [{"addSheet": {"properties": {"title": title}}}]})
            r.raise_for_status()

    def replace(self, tab: str, values: list[list[str]]) -> int:
        """Clear the tab and write all rows. Returns rows written (excluding header)."""
        self._ensure_tab(tab)
        rng = f"'{tab}'"
        self._client.post(f"{SHEETS_API}/{self.spreadsheet_id}/values/{rng}:clear", json={}).raise_for_status()
        r = self._client.put(f"{SHEETS_API}/{self.spreadsheet_id}/values/{rng}?valueInputOption=RAW",
                             json={"range": rng, "majorDimension": "ROWS", "values": values})
        r.raise_for_status()
        return max(len(values) - 1, 0)


def export_leads(leads: list[Lead], campaign_id: str, *, tab: str | None = None) -> dict:
    if not configured():
        raise RuntimeError("Google Sheets not configured: set GTM_SHEETS_CREDENTIALS_JSON and GTM_SHEETS_SPREADSHEET_ID")
    exporter = SheetsExporter(os.environ["GTM_SHEETS_SPREADSHEET_ID"], access_token())
    tab = tab or campaign_id
    n = exporter.replace(tab, rows_for(leads))
    log.info("sheets: wrote %d leads to tab %r", n, tab)
    return {"rows": n, "tab": tab, "spreadsheet_id": exporter.spreadsheet_id,
            "url": f"https://docs.google.com/spreadsheets/d/{exporter.spreadsheet_id}",
            "exported_at": datetime.now().isoformat(timespec="seconds")}
