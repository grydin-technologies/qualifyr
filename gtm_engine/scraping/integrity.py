"""Is this page really the company's live website?

A 200 response is not evidence. Domains get parked, sold, redirected to a marketplace
listing, or left as an "under construction" placeholder, and every one of those looks
reachable. Scraping them produces a confident, wrong lead – the exact failure the
quality-over-quantity rule exists to prevent – so each is detected and the lead is
demoted rather than shipped."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from gtm_engine.validation.domains import registrable_domain

# Registrar / reseller parking pages and "domain for sale" landers.
_PARKED_PHRASES = (
    "domain is for sale", "domain for sale", "buy this domain", "this domain is available",
    "is for sale", "domain name is for sale", "make an offer", "inquire about this domain",
    "parked free", "parked domain", "courtesy of godaddy", "future home of something quite cool",
    "this site is parked", "sedo", "hugedomains", "dan.com", "afternic", "namecheap parking",
    "default web site page", "apache2 ubuntu default page", "welcome to nginx",
    "index of /", "it works!", "web hosting provided by",
)
_PARKED_STRONG = ("for sale", "buy this domain", "parked")

# Placeholder sites: real domain, no business content yet.
_PLACEHOLDER_PHRASES = (
    "under construction", "coming soon", "site is being updated", "website is under maintenance",
    "launching soon", "opening soon", "be right back", "site under development",
)

# Soft 404: HTTP 200 with a not-found body.
_SOFT_404_PHRASES = (
    "404", "page not found", "page cannot be found", "page doesn't exist", "page does not exist",
    "no longer available", "nothing found", "error 404", "not found on this server",
)

# Hosts that are never a company's own site: a redirect landing here means the domain is dead.
_NOT_OWN_SITE = {
    "daraz.pk", "olx.com.pk", "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
    "tiktok.com", "amazon.com", "alibaba.com", "aliexpress.com", "etsy.com", "shopify.com",
    "godaddy.com", "sedo.com", "hugedomains.com", "dan.com", "afternic.com", "namecheap.com",
    "wix.com", "wordpress.com", "blogspot.com", "google.com", "bing.com", "yellowpages.pk",
    "businesslist.pk", "zameen.com", "rozee.pk", "indeed.com", "tradekey.com",
}

_BINARY_PREFIXES = (b"%PDF", b"\x89PNG", b"GIF8", b"\xff\xd8\xff", b"PK\x03\x04", b"\x1f\x8b", b"{\\rtf")


@dataclass
class Integrity:
    ok: bool = True
    reason: str | None = None          # machine-readable: parked | placeholder | soft_404 | binary | off_domain | thin
    detail: str = ""
    final_domain: str | None = None    # when a redirect moved us elsewhere
    notes: list[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        """Content may still be parsed (an off-domain redirect can be a real brand site)."""
        return self.reason in (None, "off_domain")


def _has(text: str, phrases) -> str | None:
    low = text.lower()
    for p in phrases:
        if p in low:
            return p
    return None


def looks_binary(text: str) -> bool:
    head = (text or "")[:64].encode("utf-8", "ignore")
    return any(head.startswith(p) for p in _BINARY_PREFIXES)


def is_parked(text: str, title: str | None = None) -> str | None:
    """Parked pages are short and shouty; a long page mentioning 'for sale' is a shop."""
    body = f"{title or ''} {text}"
    hit = _has(body, _PARKED_PHRASES)
    if hit and (len(text) < 1200 or _has(title or "", _PARKED_STRONG)):
        return hit
    return None


def is_placeholder(text: str, title: str | None = None) -> str | None:
    hit = _has(f"{title or ''} {text}", _PLACEHOLDER_PHRASES)
    return hit if hit and len(text) < 1500 else None


def is_soft_404(text: str, title: str | None = None) -> str | None:
    hit = _has(f"{title or ''} {text[:600]}", _SOFT_404_PHRASES)
    return hit if hit and len(text) < 1500 else None


def redirect_target(requested_url: str, final_url: str) -> str | None:
    """The final registrable domain when a redirect left the requested one, else None."""
    a, b = registrable_domain(requested_url), registrable_domain(final_url)
    if not b or a == b:
        return None
    return b


def check(requested_url: str, final_url: str, html: str, text: str, title: str | None = None,
          min_text_chars: int = 120) -> Integrity:
    """Order matters: a redirect to a marketplace is reported as off-domain-not-own-site,
    not as 'thin', so the reason a lead was dropped is the true one."""
    moved = redirect_target(requested_url, final_url)
    if moved and moved in _NOT_OWN_SITE:
        return Integrity(False, "off_domain_not_own", f"redirects to {moved}, which is never a company's own site",
                         final_domain=moved)
    if looks_binary(html) or looks_binary(text):
        return Integrity(False, "binary", "served a binary document, not a web page")
    hit = is_parked(text, title)
    if hit:
        return Integrity(False, "parked", f"parked or for-sale page ({hit!r})", final_domain=moved)
    hit = is_soft_404(text, title)
    if hit:
        return Integrity(False, "soft_404", f"page not found despite HTTP 200 ({hit!r})", final_domain=moved)
    hit = is_placeholder(text, title)
    if hit:
        return Integrity(False, "placeholder", f"placeholder site ({hit!r})", final_domain=moved)
    if len(text.strip()) < min_text_chars:
        return Integrity(False, "thin", f"almost no content ({len(text.strip())} chars)", final_domain=moved)
    out = Integrity(True, None, "", final_domain=moved)
    if moved:
        out.notes.append(f"redirects to {moved}")
    return out
