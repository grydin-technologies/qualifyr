"""PPRA e-procurement (epms.ppra.gov.pk): every active public tender in Pakistan with the
procuring organisation, requirement text and closing date. A tender is the strongest
intent signal there is – a stated requirement, with a deadline, from a confirmed buyer.

Used two ways:
  * as a DiscoverySource: organisations tendering for what the campaign sells become leads
  * as an enrichment: a lead whose name matches a tendering organisation gets the tender
    attached as an intent signal."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime
from typing import AsyncIterator
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from gtm_engine.config.schema import CampaignConfig, EngineSettings
from gtm_engine.intent.models import IntentSignal
from gtm_engine.models import DiscoveredCompany
from gtm_engine.scraping.fetcher import Fetcher
from gtm_engine.validation.dedupe import normalize_name

log = logging.getLogger(__name__)

PPRA_URL = "https://epms.ppra.gov.pk/public/tenders/active-tenders"
CACHE_TTL_S = 24 * 3600
_DATE_FMTS = ("%b %d, %Y %I:%M %p", "%b %d, %Y")


def _date(text: str) -> str | None:
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(text.strip(), fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_ppra(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    out: list[dict] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue
        cells = [td.get_text(" ", strip=True) for td in tds]
        link = tr.find("a", href=True)
        out.append({
            "tender_no": cells[1], "details": cells[2], "organization": cells[3], "status": cells[4],
            "advertised": _date(cells[5]), "closing": _date(cells[6]),
            "url": link["href"] if link and link["href"].startswith("http") else PPRA_URL,
        })
    return out


def is_open(tender: dict, today: str | None = None) -> bool:
    """PPRA's 'active' list keeps tenders for 10 days after closing; a closed tender is history."""
    closing = tender.get("closing")
    if not closing:
        return True
    return closing >= (today or datetime.now().date().isoformat())


def matches_campaign(tender: dict, campaign: CampaignConfig) -> list[str]:
    """Campaign terms found in the tender text (industries, buyer keywords, intent keywords)."""
    text = f"{tender['details']} {tender['organization']}".lower()
    terms = set(campaign.target_industries) | set(campaign.intent_keywords)
    return sorted({t for t in terms if t and re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", text)})


_ABBR_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<abbr>[A-Z&.\- ]{2,12})\)(?P<rest>.*)$")


def clean_org(name: str) -> str:
    """'Pakistan State Oil (PSO) PSO Karachi' -> 'Pakistan State Oil';
    'Ministry of Finance Pakistan Revenue Automation' stays; trailing repeats are dropped."""
    name = " ".join(name.split())
    m = _ABBR_RE.match(name)
    if m:
        return m.group("name").strip(" -,")
    words = name.split()
    # 'X Y Z X Y Z' style repetition
    half = len(words) // 2
    if half >= 2 and words[:half] == words[half:2 * half]:
        return " ".join(words[:half])
    return name


def to_signal(tender: dict, matched: list[str]) -> IntentSignal:
    return IntentSignal(
        kind="tender", source="ppra", source_url=tender["url"],
        text=f"{tender['tender_no']}: {tender['details']}",
        organization=tender["organization"], date=tender["advertised"], deadline=tender["closing"],
        matched_terms=matched,
    )


class PPRATenders:
    name = "ppra"

    def __init__(self, fetcher: Fetcher, settings: EngineSettings):
        self.fetcher = fetcher
        self.cache = settings.db_path.parent / "cache" / "ppra_active_tenders.json"
        self.max_pages = 6  # per keyword; PPRA shows 50 per page

    async def tenders(self, keywords: list[str] | None = None) -> list[dict]:
        """Active tenders. With keywords, uses PPRA's own server-side keyword filter (one
        query per keyword, following pagination); without, the first pages of everything.
        Results are cached for a day per keyword set."""
        key = ",".join(sorted(k.lower() for k in keywords)) if keywords else "*"
        cache = self.cache.with_name(f"ppra_{abs(hash(key)) % 10**8}.json")
        if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_TTL_S:
            return json.loads(cache.read_text(encoding="utf-8"))
        rows: dict[str, dict] = {}
        queries = [f"{PPRA_URL}?keyword={quote_plus(k)}" for k in keywords] if keywords else [PPRA_URL]
        for base in queries:
            for page in range(1, self.max_pages + 1):
                url = f"{base}{'&' if '?' in base else '?'}page={page}"
                result = await self.fetcher.get(url, api=True, delay=1.5)
                if not result.ok:
                    log.warning("ppra: fetch failed (%s %s) for %s", result.status_code, result.error, url)
                    break
                batch = parse_ppra(result.text)
                for t in batch:
                    rows.setdefault(t["tender_no"], t)
                if len(batch) < 50:
                    break
        out = list(rows.values())
        if out or not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(out), encoding="utf-8")
        log.info("ppra: %d active tenders for %s", len(out), key)
        return out

    async def discover(self, campaign: CampaignConfig) -> AsyncIterator[DiscoveredCompany]:
        """Organisations with at least one tender matching the campaign, one company per org."""
        seen: set[str] = set()
        for t in await self.tenders(campaign.intent_keywords or campaign.target_industries or None):
            matched = matches_campaign(t, campaign)
            if not matched or not is_open(t):
                continue
            key = normalize_name(clean_org(t["organization"]))
            if key in seen:
                continue
            seen.add(key)
            country = campaign.geography.countries[0] if campaign.geography.countries else "Pakistan"
            yield DiscoveredCompany(
                name=clean_org(t["organization"]), country=country, city=None, category="tender=ppra",
                source="ppra", source_url=t["url"],
                extra={"intent": to_signal(t, matched).model_dump(mode="json")},
            )

    async def signals_for(self, company_name: str, campaign: CampaignConfig) -> list[IntentSignal]:
        """Tenders whose organisation name contains the company name (or vice versa)."""
        key = normalize_name(company_name)
        if len(key) < 5:
            return []
        out: list[IntentSignal] = []
        for t in await self.tenders(campaign.intent_keywords or campaign.target_industries or None):
            org = normalize_name(clean_org(t["organization"]))
            if (key in org or org in key) and is_open(t):
                out.append(to_signal(t, matches_campaign(t, campaign)))
        return out[:5]
