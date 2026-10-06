"""Deterministic reply classification. No model, no guessing: each label is a set of
phrases, checked in a fixed priority order, and every decision carries the phrase that
fired so the reviewer can see why. Unmatched replies are still replies – a human reads them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_QUOTE_CUT = re.compile(r"(?im)^(on .{5,120} wrote:|-{2,} ?original message ?-{2,}|from: .+|> ).*$")

LABELS = ("unsubscribe", "out_of_office", "wrong_person", "not_interested", "interested", "auto_reply", "reply")

_RULES: dict[str, list[str]] = {
    "unsubscribe": [
        r"\bunsubscribe\b", r"\bremove me\b", r"\bopt[ -]?out\b", r"\bdon'?t (email|contact|message) (me|us)\b",
        r"\bstop (emailing|contacting|sending)\b", r"^\s*stop\s*[.!]?\s*$", r"\btake (me|us) off\b",
    ],
    "out_of_office": [
        r"\bout of (the )?office\b", r"\bon (annual |sick |maternity |paternity )?leave\b", r"\bon vacation\b",
        r"\bon holiday\b", r"\bautomatic reply\b", r"\baway from (my |the )?(office|desk|email)\b",
        r"\blimited access to (my )?email\b", r"\bwill (be )?(back|return)(ing)? (on|from)\b",
    ],
    "wrong_person": [
        r"\bnot the (right|correct|appropriate) (person|contact)\b", r"\bwrong (person|department|contact)\b",
        r"\bplease (contact|reach out to|get in touch with|email|write to)\b", r"\bforward(ed|ing)? (this|your (email|message)) to\b",
        r"\b(no longer|not) (work|working|with|at|responsible|handle|handling)\b", r"\bhas (left|moved)\b",
        r"\byou (should|can|may) (contact|speak to|talk to|reach)\b", r"\bin charge of\b", r"\blooks after\b",
        r"\bdeal(s)? with (this|that|these)\b", r"\bbetter (placed|positioned|suited)\b",
    ],
    "not_interested": [
        r"\bnot interested\b", r"\bno,? thanks?\b", r"\bno thank you\b", r"\bnot (looking|in the market)\b",
        r"\bnot (a )?(fit|priority|relevant)\b", r"\balready (have|use|using|working with|sorted|covered)\b",
        r"\bwe'?re (fine|good|ok|okay)\b", r"\bno (need|requirement)\b", r"\bnot (at this time|right now|for us)\b",
        r"\bplease (do not|don'?t) follow up\b", r"\bnot required\b",
    ],
    "interested": [
        r"\binterested\b", r"\btell me more\b", r"\bsend (me |us |over )?(more |the )?(details|information|info|deck|proposal|pricing|price|quote|brochure)\b",
        r"\blet'?s (talk|discuss|connect|schedule|set up|do)\b", r"\b(book|schedule|arrange|set up) a (call|meeting|demo)\b",
        r"\bcall me\b", r"\bwhat('?s| is) the (price|cost|pricing)\b", r"\bhow (much|does it work)\b",
        r"\b(sounds|looks) (good|great|interesting)\b", r"\bwould (like|love) to\b", r"\bkeen\b", r"\bplease share\b",
        r"\bwhen (are you|can we|would you)\b", r"\bavailable (on|at|this|next)\b", r"\bdemo\b",
    ],
    "auto_reply": [
        r"\bthank you for (contacting|reaching out|your (email|message|enquiry|inquiry))\b",
        r"\bwe (have|'ve) received your (email|message|enquiry|inquiry|request)\b", r"\bticket (number|#|id)\b",
        r"\bwill (get back|respond|reply) to you (shortly|soon|within)\b", r"\bthis is an automated\b",
        r"\bdo not reply to this\b", r"\bcase (number|#)\b",
    ],
}
_COMPILED = {label: [re.compile(p, re.I) for p in pats] for label, pats in _RULES.items()}

_DATE_PATTERNS = [
    re.compile(r"\b(?:back|return(?:ing)?|until|till)\s+(?:on\s+|in the office on\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:\s+(\d{4}))?", re.I),
    re.compile(r"\b(?:back|return(?:ing)?|until|till)\s+(?:on\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?", re.I),
    re.compile(r"\b(?:back|return(?:ing)?|until|till)\s+(?:on\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", re.I),
]
_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


@dataclass
class Classification:
    label: str
    matched: str = ""
    referred_email: str | None = None
    referred_name: str | None = None
    return_date: datetime | None = None
    extras: dict = field(default_factory=dict)


def strip_quoted(body: str) -> str:
    """Only the fresh text matters; quoted history contains our own words."""
    lines = []
    for line in (body or "").splitlines():
        if _QUOTE_CUT.match(line.strip()):
            break
        lines.append(line)
    return "\n".join(lines)


def parse_return_date(text: str, now: datetime) -> datetime | None:
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        g = m.groups()
        try:
            if pat is _DATE_PATTERNS[0]:
                day, mon, year = int(g[0]), _MONTHS[g[1][:3].lower()], int(g[2]) if g[2] else now.year
            elif pat is _DATE_PATTERNS[1]:
                mon, day, year = _MONTHS[g[0][:3].lower()], int(g[1]), int(g[2]) if g[2] else now.year
            else:
                day, mon = int(g[0]), int(g[1])
                year = int(g[2]) if g[2] else now.year
                if year < 100:
                    year += 2000
            dt = datetime(year, mon, day, tzinfo=now.tzinfo)
            if dt < now - timedelta(days=1) and not (g[2] if len(g) > 2 else None):
                dt = dt.replace(year=now.year + 1)  # "back on 3 Jan" said in December
            return dt
        except (ValueError, KeyError):
            continue
    return None


def _referral(text: str, own_email: str | None, sender: str | None) -> tuple[str | None, str | None]:
    emails = [e.lower() for e in _EMAIL_RE.findall(text)]
    emails = [e for e in emails if e != (own_email or "").lower() and e != (sender or "").lower()]
    if not emails:
        return None, None
    email = emails[0]
    # A name is usually just before the address: "contact Ahmed Raza (ahmed@...)" / "Ahmed Raza - ahmed@"
    m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s*[\(\-––,:]?\s*" + re.escape(email), text)
    return email, (m.group(1) if m else None)


def classify(subject: str, body: str, *, own_email: str | None = None, sender: str | None = None,
             now: datetime | None = None) -> Classification:
    now = now or datetime.now()
    fresh = strip_quoted(body)
    text = f"{subject or ''}\n{fresh}"
    low = text.lower()
    for label in LABELS[:-1]:
        for pat in _COMPILED[label]:
            m = pat.search(text)
            if not m:
                continue
            c = Classification(label=label, matched=m.group(0)[:60])
            if label == "out_of_office":
                c.return_date = parse_return_date(fresh, now)
            if label == "wrong_person":
                c.referred_email, c.referred_name = _referral(fresh, own_email, sender)
            return c
    # An address offered without any "wrong person" wording is still a referral worth surfacing.
    email, name = _referral(fresh, own_email, sender)
    if email and email.split("@", 1)[1] == (sender or "@").split("@", 1)[1] and len(low) < 600:
        return Classification(label="wrong_person", matched=f"address offered: {email}", referred_email=email, referred_name=name)
    return Classification(label="reply")
