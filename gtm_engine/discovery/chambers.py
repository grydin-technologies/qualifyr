"""Chamber-of-commerce member directories as discovery sources (Pakistan).

KCCI (Karachi) publishes its full active-member list on one public page with the member
company and its registered representative – usually the owner or a director, i.e. the
decision-maker we want. The page is ~3 MB and changes rarely, so it is cached on disk.

LCCI (Lahore) and ICCI (Islamabad) do not expose a scrapeable list without a session; they
are recorded as not-yet-supported rather than faked."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import AsyncIterator

from bs4 import BeautifulSoup

from gtm_engine.config.schema import CampaignConfig, EngineSettings
from gtm_engine.models import DiscoveredCompany
from gtm_engine.scraping.fetcher import Fetcher

log = logging.getLogger(__name__)

KCCI_URL = "https://www.kcci.com.pk/active-members.php"
CACHE_TTL_S = 7 * 24 * 3600

_LEGAL_TAIL = re.compile(r"\s*\((pvt|private)\.?\)?\s*(ltd|limited)\.?$|\s*(pvt\.?|private)\s*(ltd|limited)\.?$|\s*(ltd|limited|llc|inc)\.?$", re.I)


def parse_kcci(html: str) -> list[dict]:
    """Rows of {msno, company, representative} from the KCCI active-members table."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []
    out: list[dict] = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) < 3 or not cells[0].isdigit():
            continue
        company, rep = cells[1].strip(), cells[2].strip()
        if not company:
            continue
        out.append({"msno": cells[0], "company": company, "representative": rep or None})
    return out


def title_case(name: str) -> str:
    """'PIONEER CEMENT LTD.' -> 'Pioneer Cement Ltd.' (directories shout)."""
    small = {"of", "and", "&", "the", "for"}
    words = []
    for w in name.split():
        lw = w.lower()
        if w.isupper() and len(w.replace(".", "")) <= 4 and w.replace(".", "").isalpha() and w not in ("LTD", "PVT", "INC"):
            words.append(w)  # acronyms: ACT, A.C.T., KCCI
        else:
            words.append(lw if lw in small else w[:1].upper() + w[1:].lower())
    return " ".join(words)


def clean_rep(rep: str | None) -> str | None:
    if not rep:
        return None
    rep = re.sub(r"^(mr|mrs|ms|dr|engr|prof|haji)\.?\s+", "", rep.strip(), flags=re.I).rstrip(" .,;")
    return " ".join(w[:1].upper() + w[1:].lower() if w.isupper() else w for w in rep.split()) or None


def name_matches_campaign(company: str, campaign: CampaignConfig) -> bool:
    """Directories have no sector field; the company name is the only industry hint."""
    terms = set(campaign.target_industries) | set(campaign.buyer_keywords) | set(campaign.chamber_name_keywords)
    if not terms:
        return True
    low = company.lower()
    return any(t and t in low for t in terms)


class KCCIDirectory:
    name = "kcci"

    def __init__(self, fetcher: Fetcher, settings: EngineSettings):
        self.fetcher = fetcher
        self.cache = settings.db_path.parent / "cache" / "kcci_active_members.json"

    async def _rows(self) -> list[dict]:
        if self.cache.exists() and time.time() - self.cache.stat().st_mtime < CACHE_TTL_S:
            return json.loads(self.cache.read_text(encoding="utf-8"))
        result = await self.fetcher.get(KCCI_URL, api=True)
        if not result.ok:
            log.warning("kcci: fetch failed (%s %s)", result.status_code, result.error)
            return json.loads(self.cache.read_text(encoding="utf-8")) if self.cache.exists() else []
        rows = parse_kcci(result.text)
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(json.dumps(rows), encoding="utf-8")
        log.info("kcci: %d active members cached", len(rows))
        return rows

    async def discover(self, campaign: CampaignConfig) -> AsyncIterator[DiscoveredCompany]:
        if "karachi" not in {c.lower() for c in campaign.geography.cities}:
            return
        matched = 0
        for row in await self._rows():
            if not name_matches_campaign(row["company"], campaign):
                continue
            matched += 1
            yield DiscoveredCompany(
                name=title_case(_LEGAL_TAIL.sub("", row["company"])) or row["company"],
                country=campaign.geography.countries[0] if campaign.geography.countries else "Pakistan",
                city="Karachi",
                category="chamber=kcci",
                source="kcci",
                source_url=KCCI_URL,
                extra={"legal_name": row["company"], "representative": clean_rep(row["representative"]),
                       "membership_no": row["msno"]},
            )
        log.info("kcci: %d members matched the campaign's industry/buyer terms", matched)
