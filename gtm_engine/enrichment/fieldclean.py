"""Deterministic field cleaning for human-shareable output.

Discovery and scraping produce raw, machine-shaped values – meta descriptions mixed
with nav-menu scrapes, URL-encoded e-mail fragments, multi-line concatenated addresses,
non-Latin company names, and `key: value` signal tags. These functions turn those into
clean, readable cells so an exported sheet is usable by a non-technical reader. Everything
here is pure and side-effect free (easy to unit-test); nothing invents facts.
"""

from __future__ import annotations

import re
from urllib.parse import unquote

# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

def clean_address(addr: str | None) -> str | None:
    """Collapse whitespace, drop newlines, and keep the FIRST address when several are
    concatenated (sites list every branch). Returns None for empty input."""
    if not addr:
        return None
    # Two-or-more line breaks separate distinct addresses; keep the first.
    first = re.split(r"(?:\r?\n){2,}", addr.strip())[0]
    s = re.sub(r"\s+", " ", first.replace("\n", " ")).strip()
    s = s.strip(" ,،-")
    return s[:160] or None


# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------

def clean_email(email: str | None) -> str | None:
    """Repair the common ways a harvested address arrives malformed:
      - URL-encoded prefixes ("%20contact@x.pk" -> "contact@x.pk")
      - a phone number fused to the local part ("03009502334info@x.com" -> "info@x.com")
      - surrounding punctuation / whitespace
    Returns a lowercased address, or None if nothing salvageable remains.
    Validation (syntax + MX) still happens downstream – this only normalises the string.
    """
    if not email:
        return None
    e = unquote(email).strip().strip(".,;:<>()[]\"' ")
    e = re.sub(r"\s+", "", e)
    if e.count("@") != 1:
        return None
    local, domain = e.split("@")
    # A long leading digit run fused to letters is a phone number stuck to the address.
    m = re.match(r"^\+?\d[\d\s().-]{4,}([A-Za-z].*)$", local)
    if m:
        local = m.group(1)
    local = local.lstrip("._-")
    if not local or not domain or "." not in domain:
        return None
    return f"{local}@{domain}".lower()


# ---------------------------------------------------------------------------
# Descriptions / boilerplate
# ---------------------------------------------------------------------------

_NAV_TOKENS = {
    "skip", "content", "home", "menu", "cart", "login", "logout", "account",
    "about", "contact", "story", "stories", "products", "product", "shop",
    "search", "toggle", "navigation", "sidebar", "newsletter", "subscribe",
    "us", "our", "blog", "faq", "faqs", "wishlist", "checkout", "categories",
}


def looks_like_boilerplate(text: str) -> bool:
    """True when the text is a scraped nav menu / chrome rather than a real description."""
    t = (text or "").strip().lower()
    if not t:
        return True
    if t.startswith(("skip to content", "skip to main", "toggle navigation", "main menu")):
        return True
    words = re.findall(r"[a-z']+", t[:220])
    if len(words) < 4:
        return False
    nav = sum(1 for w in words if w in _NAV_TOKENS)
    # A real sentence rarely opens with a dense cluster of nav words.
    return nav >= 4 and nav / len(words) > 0.18


def _first_sentences(text: str, limit: int) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # Prefer to end on a sentence boundary, else the last word boundary.
    dot = cut.rfind(". ")
    if dot >= 60:
        return cut[: dot + 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp >= 60 else cut).rstrip() + "…"


def clean_description(meta: str | None, research_brief: str | None = None) -> str | None:
    """A clean one-liner about the company. Prefers the page meta description when it reads
    like real prose; otherwise falls back to the grounded research brief. Never returns a
    nav-menu scrape – better an empty cell than junk."""
    m = re.sub(r"\s+", " ", meta).strip() if meta else ""
    if len(m) >= 40 and not looks_like_boilerplate(m):
        return _first_sentences(m, 280)
    if research_brief:
        rb = re.sub(r"\s+", " ", research_brief).strip()
        if rb:
            return _first_sentences(rb, 280)
    return None


# ---------------------------------------------------------------------------
# Company name (prefer a Latin-script rendering)
# ---------------------------------------------------------------------------

def _latin_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if ord(c) < 128) / len(letters)


def _clean_title(title: str) -> str:
    # Site titles tack on " - Home", " | Welcome", taglines – keep the first segment.
    seg = re.split(r"\s[|\-––:]\s", title.strip())[0].strip()
    seg = re.sub(r"\b(home|welcome|official website|homepage)\b", "", seg, flags=re.I).strip()
    return seg or title.strip()


def prefer_latin_name(name: str | None, *alternatives: str | None) -> str:
    """Return a readable Latin-script name. If `name` is mostly non-Latin (Urdu/Arabic),
    fall back to the first alternative (e.g. page title) that is predominantly Latin."""
    name = (name or "").strip()
    if name and _latin_ratio(name) >= 0.5:
        return name
    for alt in alternatives:
        if alt and _latin_ratio(alt) >= 0.6:
            return _clean_title(alt)
    return name


# ---------------------------------------------------------------------------
# Human-readable category / score reason / signals
# ---------------------------------------------------------------------------

def humanize_industry(industry: str | None) -> str:
    """'overture=health_care' -> 'Health Care'; 'shop=supermarket' -> 'Supermarket'."""
    if not industry:
        return ""
    val = industry.split("=", 1)[-1]
    return val.replace("_", " ").replace("-", " ").strip().title()


def clean_reason(score_reason: str | None) -> str:
    """Strip internal plumbing from the score reason for a client-facing 'why qualified':
    the proximity-tier debug note and the redundant 'classified as X' tail."""
    if not score_reason:
        return ""
    parts = [p.strip() for p in score_reason.split(";")]
    kept = []
    for p in parts:
        low = p.lower()
        if low.startswith("tier ") and "anchor" in low:
            continue
        if low.startswith("classified as "):
            continue
        if p:
            kept.append(p)
    return "; ".join(kept)
