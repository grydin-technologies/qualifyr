"""Email validation without paid APIs: syntax, domain sanity and MX lookup.
An address is never 'verified' merely because it contains '@'."""

from __future__ import annotations

import asyncio
import re

import dns.asyncresolver
import dns.exception

from gtm_engine.models import EmailStatus
from gtm_engine.validation.domains import canonical_domain

EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9.-])"
)

# File extensions that regularly show up as "email-like" tokens in HTML (e.g. image@2x.png).
_JUNK_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js")
FREEMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "protonmail.com", "proton.me", "ymail.com", "msn.com", "aol.com",
}
_JUNK_DOMAINS = {"example.com", "email.com", "domain.com", "yourdomain.com", "sentry.io", "wixpress.com"}


def _mangled(email: str, source: str) -> bool:
    """True when the matched address is a fragment of something with non-ASCII characters
    (Cyrillic lookalikes, zero-width joiners). 'іnfo@x.pk' would otherwise be harvested as
    'nfo@x.pk' – an address that silently bounces."""
    i = source.lower().find(email)
    if i <= 0:
        return False
    before = source[i - 1]
    return not before.isspace() and (ord(before) > 127 or before.isalnum())


def extract_emails(text: str) -> list[str]:
    from gtm_engine.enrichment.fieldclean import clean_email

    seen: list[str] = []
    source = text or ""
    for match in EMAIL_RE.findall(source):
        email = match.lower().strip(".")
        if _mangled(email, source):
            continue
        if email.endswith(_JUNK_SUFFIXES):
            continue
        # Repair URL-encoding leaks and phone-numbers fused to the local part.
        cleaned = clean_email(email)
        if not cleaned or cleaned.endswith(_JUNK_SUFFIXES):
            continue
        email = cleaned
        domain = email.split("@", 1)[1]
        if domain in _JUNK_DOMAINS or canonical_domain(domain) is None:
            continue
        if email not in seen:
            seen.append(email)
    return seen


def is_syntax_valid(email: str) -> bool:
    if not email or email.count("@") != 1 or len(email) > 254:
        return False
    local, domain = email.split("@")
    if not local or len(local) > 64 or ".." in email:
        return False
    return EMAIL_RE.fullmatch(email) is not None and canonical_domain(domain) is not None


def is_generic_mailbox(email: str, generic_prefixes: list[str]) -> bool:
    local = email.split("@", 1)[0].lower()
    return local in set(generic_prefixes)


class MXChecker:
    """Async MX lookup with an in-process cache so one domain is resolved once per run."""

    def __init__(self, timeout_s: float = 5.0):
        self._resolver = dns.asyncresolver.Resolver()
        self._resolver.lifetime = timeout_s
        self._cache: dict[str, bool] = {}
        self._lock = asyncio.Lock()

    async def has_mx(self, domain: str) -> bool:
        domain = domain.lower()
        if domain in self._cache:
            return self._cache[domain]
        async with self._lock:
            if domain in self._cache:
                return self._cache[domain]
            result = await self._lookup(domain)
            self._cache[domain] = result
            return result

    async def _lookup(self, domain: str) -> bool:
        try:
            answers = await self._resolver.resolve(domain, "MX")
            return any(str(r.exchange).strip(".") not in ("", "0") for r in answers)
        except dns.exception.DNSException:
            # Some small businesses accept mail on the A record; treat an A record as weak positive.
            try:
                await self._resolver.resolve(domain, "A")
                return True
            except dns.exception.DNSException:
                return False


async def classify_email(email: str | None, generic_prefixes: list[str],
                         mx: MXChecker | None) -> EmailStatus:
    if not email:
        return EmailStatus.NONE
    if not is_syntax_valid(email):
        return EmailStatus.INVALID
    if mx is None:
        return EmailStatus.UNVERIFIED
    domain = email.split("@", 1)[1]
    if not await mx.has_mx(domain):
        return EmailStatus.INVALID
    if is_generic_mailbox(email, generic_prefixes):
        return EmailStatus.GENERIC
    return EmailStatus.MX_VALID

