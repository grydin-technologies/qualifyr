"""HTML extraction: visible text, description, emails, phones, social links, team members.
Pure functions over HTML strings so they are trivially testable."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from gtm_engine.validation.emails import extract_emails

_NOISE_TAGS = ("script", "style", "noscript", "svg", "iframe", "template", "head")

# Pakistan / GCC formats plus international. Requires 9-13 digits so prices don't match.
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?(?:92|971|966|974|968)[\s().-]*\d(?:[\s().-]*\d){8,10}|0\d{2,3}[\s().-]*\d{7,8}|0\d{3}[\s.-]?\d{7})(?!\d)"
)

SOCIAL_PATTERNS = {
    "linkedin": re.compile(r"(?:www\.)?linkedin\.com/(?:company|in)/[^/?#\s\"']+", re.I),
    "facebook": re.compile(r"(?:www\.)?facebook\.com/[^/?#\s\"']+", re.I),
    "instagram": re.compile(r"(?:www\.)?instagram\.com/[^/?#\s\"']+", re.I),
    "whatsapp": re.compile(r"(wa\.me/\d+|api\.whatsapp\.com/send\?phone=\d+)", re.I),
}

PAGE_KIND_HINTS: dict[str, tuple[str, ...]] = {
    "about": ("about", "who-we-are", "our-story", "company", "overview", "profile"),
    "contact": ("contact", "reach-us", "get-in-touch", "locations", "branches", "store-locator"),
    "team": ("team", "leadership", "management", "our-people", "board", "directors", "founders"),
    "services": ("services", "products", "solutions", "what-we-do", "collections", "shop", "catalog"),
    "careers": ("career", "careers", "jobs", "join-us", "hiring", "vacanc"),
}

# Words in a link's own text that identify the page kind even when the URL is opaque.
_LINK_TEXT_HINTS: dict[str, tuple[str, ...]] = {
    "about": ("about", "who we are", "our story", "company"),
    "contact": ("contact", "get in touch", "reach us", "visit us", "locations", "branches"),
    "team": ("team", "leadership", "management", "our people", "directors", "founders"),
    "services": ("services", "products", "solutions", "what we do"),
    "careers": ("career", "jobs", "join us", "we are hiring"),
}


@dataclass
class ParsedPage:
    url: str
    title: str | None
    description: str | None
    text: str
    emails: list[str] = field(default_factory=list)          # visible text or mailto:
    source_emails: list[str] = field(default_factory=list)   # only in raw HTML (scripts, licences, credits)
    phones: list[str] = field(default_factory=list)
    social: dict[str, str] = field(default_factory=dict)
    profiles: list[str] = field(default_factory=list)              # personal linkedin /in/ links
    internal_links: dict[str, str] = field(default_factory=dict)  # kind -> absolute url
    team: list[tuple[str, str]] = field(default_factory=list)      # (name, role)


def visible_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def meta_description(soup: BeautifulSoup) -> str | None:
    for attrs in ({"name": "description"}, {"property": "og:description"}, {"name": "twitter:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content") and tag["content"].strip():
            return tag["content"].strip()[:500]
    return None


def classify_link(href: str, text: str) -> str | None:
    path = urlparse(href).path.lower()
    text_l = (text or "").lower().strip()
    for kind, hints in _LINK_TEXT_HINTS.items():
        if text_l and any(text_l == h or text_l.startswith(h) for h in hints):
            return kind
    for kind, hints in PAGE_KIND_HINTS.items():
        if any(h in path for h in hints):
            return kind
    return None


def internal_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    found: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        host = urlparse(absolute).netloc.lower().removeprefix("www.")
        if host != base_host:
            continue
        kind = classify_link(absolute, a.get_text(" ", strip=True))
        if kind and kind not in found:
            found[kind] = absolute.split("#")[0]
    return found


def social_links(html: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, pattern in SOCIAL_PATTERNS.items():
        m = pattern.search(html)
        if m:
            out[name] = "https://" + m.group(0)
    return out


_PERSONAL_LINKEDIN = re.compile(r"(?:www\.)?linkedin\.com/in/[a-z0-9%\-_.]+", re.I)


def personal_profiles(html: str) -> list[str]:
    """Every personal LinkedIn (/in/<slug>) link on the page – a person's profile, not the
    company's (/company/) page. Used to attach a decision-maker's own profile to them."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _PERSONAL_LINKEDIN.finditer(html or ""):
        url = "https://" + m.group(0).lstrip("wW.")
        key = url.lower()
        if key not in seen:
            seen.add(key)
            out.append(url)
    return out


def extract_phones(text: str) -> list[str]:
    seen: list[str] = []
    for m in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", m)
        if 9 <= len(digits) <= 13 and m.strip() not in seen:
            seen.append(m.strip())
    return seen[:5]


_ROLE_WORDS = (
    "founder", "ceo", "chief", "director", "manager", "head", "president", "owner",
    "chairman", "partner", "officer", "lead", "principal", "proprietor", "gm", "md",
    "coo", "cfo", "cto", "vp", "vice", "executive", "specialist", "coordinator", "engineer",
    "analyst", "associate", "consultant", "supervisor", "accountant", "secretary", "sales",
)
_ROLE_RE = re.compile(r"(?<![a-z])(?:" + "|".join(re.escape(w) for w in _ROLE_WORDS) + r")(?![a-z])")
# Capitalised phrases that are headings/products, never people.
_NOT_NAME_WORDS = {
    "items", "item", "products", "product", "collection", "collections", "sale", "offer", "offers",
    "new", "shop", "store", "cart", "menu", "home", "about", "contact", "category", "categories",
    "brand", "brands", "price", "free", "delivery", "order", "orders", "login", "register", "search",
    "best", "top", "latest", "featured", "arrivals", "deals", "gift", "gifts", "pack", "packs",
    "welcome", "our", "team", "services", "service", "solutions", "read", "more", "view", "all",
    "privacy", "policy", "terms", "faq", "faqs", "blog", "news", "careers", "subscribe",
}
_NAME_RE = re.compile(r"^(?:Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Engr\.?|Prof\.?|Syed|Muhammad|Mohammad)?\s*[A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){0,4}$")


def _looks_like_name(s: str) -> bool:
    s = s.strip()
    if not (3 <= len(s) <= 60 and _NAME_RE.match(s)):
        return False
    words = {w.lower().strip(".,'") for w in s.split()}
    return not (words & _NOT_NAME_WORDS) and not _ROLE_RE.search(s.lower())


def _looks_like_role(s: str) -> bool:
    s = s.strip().lower()
    return 2 <= len(s) <= 80 and not any(ch.isdigit() for ch in s) and _ROLE_RE.search(s) is not None


_INLINE_SEP = r"\s*(?:,|–|–|-|:|\|)\s*"
_INLINE_TITLES = (
    "founder & ceo", "co-founder", "cofounder", "founder", "chief executive officer", "ceo",
    "managing director", "general manager", "chief operating officer", "coo", "director",
    "owner", "proprietor", "chairman", "president", "head of ecommerce", "operations manager",
    "procurement manager", "purchasing manager", "principal", "medical director",
)
_INLINE_TITLE_ALT = "|".join(re.escape(t) for t in sorted(_INLINE_TITLES, key=len, reverse=True))
_INLINE_NAME = r"(?:Dr\.?\s|Mr\.?\s|Mrs\.?\s|Ms\.?\s|Engr\.?\s)?[A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,3}"
_INLINE_NAME_TITLE = re.compile(rf"({_INLINE_NAME}){_INLINE_SEP}((?i:{_INLINE_TITLE_ALT}))(?![a-zA-Z])")
_INLINE_TITLE_NAME = re.compile(rf"(?<![a-zA-Z])((?i:{_INLINE_TITLE_ALT})){_INLINE_SEP}({_INLINE_NAME})")


def extract_inline_team(text: str) -> list[tuple[str, str]]:
    """'Ahmed Raza, CEO' or 'CEO: Ahmed Raza' inside running prose (about pages)."""
    pairs: list[tuple[str, str]] = []
    for pat, name_first in ((_INLINE_NAME_TITLE, True), (_INLINE_TITLE_NAME, False)):
        for m in pat.finditer(text):
            name, role = (m.group(1), m.group(2)) if name_first else (m.group(2), m.group(1))
            name = name.strip()
            if _looks_like_name(name) and (name, role) not in pairs:
                pairs.append((name, role))
    return pairs[:10]


def extract_team(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Find (name, role) pairs from team-card style markup: a heading/strong element
    holding a name followed by a short sibling holding a role. Deliberately strict."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    candidates = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "p", "span", "div"])
    for el in candidates:
        name = el.get_text(" ", strip=True)
        if not _looks_like_name(name):
            continue
        role = None
        # Look at the next few short elements after the name for a role.
        for sib in el.find_all_next(["p", "span", "div", "small", "em", "h4", "h5", "h6"], limit=4):
            txt = sib.get_text(" ", strip=True)
            if not txt or txt == name:
                continue
            if _looks_like_role(txt):
                role = txt
            break
        if role and name not in seen:
            seen.add(name)
            pairs.append((name, role))
    return pairs[:20]


def parse_page(url: str, html: str) -> ParsedPage:
    soup = BeautifulSoup(html or "", "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    description = meta_description(soup)
    links = internal_links(soup, url)
    team = extract_team(BeautifulSoup(html or "", "lxml"))
    social = social_links(html or "")
    # mailto: links are the most reliable email source; scan them before the visible text.
    mailto = [a["href"][7:].split("?")[0] for a in soup.find_all("a", href=True) if a["href"].lower().startswith("mailto:")]
    text = visible_text(soup)
    for pair in extract_inline_team(text):
        if pair[0] not in {n for n, _ in team}:
            team.append(pair)
    emails = extract_emails(" ".join(mailto) + " " + text)
    source_emails = [e for e in extract_emails(html or "") if e not in emails]
    phones = extract_phones(text)
    return ParsedPage(
        url=url, title=title, description=description, text=text[:20000],
        emails=emails, source_emails=source_emails, phones=phones, social=social,
        profiles=personal_profiles(html or ""), internal_links=links, team=team,
    )
