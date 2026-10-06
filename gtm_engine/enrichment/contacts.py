"""Pick the most relevant decision-maker from public company pages. Only names and
roles the company itself publishes; nothing is guessed."""

from __future__ import annotations

from gtm_engine.config.schema import CampaignConfig, DefaultRules
from gtm_engine.models import Contact, EmailStatus
from gtm_engine.scraping.site_crawler import SiteSnapshot
from gtm_engine.enrichment.phones import best_phone
from gtm_engine.validation.domains import domain_label
from gtm_engine.validation.emails import FREEMAIL_DOMAINS, is_generic_mailbox


def usable_emails(visible: list[str], company_domain: str | None, source_only: list[str] = ()) -> list[str]:
    """Own-domain addresses first (same registered label counts: bata.com for bata.com.pk),
    then freemail seen in visible text (common for SMEs). Anything else is dropped: on a
    company site third-party addresses are web-developer credits, plugin authors, font
    licences. Freemail found only in raw HTML is never trusted for the same reason."""
    label = domain_label(company_domain) if company_domain else None

    def is_own(e: str) -> bool:
        d = e.split("@", 1)[1]
        return bool(company_domain) and (d == company_domain or (label is not None and domain_label(d) == label))

    own = [e for e in visible if is_own(e)] + [e for e in source_only if is_own(e)]
    free = [e for e in visible if e.split("@", 1)[1] in FREEMAIL_DOMAINS]
    return own + [e for e in free if e not in own]


def role_rank(role: str, campaign: CampaignConfig, defaults: DefaultRules) -> int:
    """Higher is better. -1 means the role is on the sell side and must be dropped."""
    r = role.lower()
    if any(b in r for b in defaults.role_blacklist):
        return -1
    score = 0
    for i, target in enumerate(campaign.target_roles):
        if target and target in r:
            score = max(score, 100 - i)  # campaign order expresses preference
    for i, allowed in enumerate(defaults.buyer_role_whitelist):
        if allowed in r:
            score = max(score, 50 - min(i, 40))
    return score


def _match_personal_profile(name: str, profiles: list[str]) -> str | None:
    """A decision-maker's own LinkedIn, matched by name. Requires BOTH the first and last
    name in the /in/ slug so we never attach a stranger's profile – a missed match just
    falls back to the company page, which is the safe failure."""
    parts = [p for p in name.lower().replace(".", " ").split() if p.isalpha()]
    if len(parts) < 2:
        return None
    first, last = parts[0], parts[-1]
    for url in profiles:
        slug = url.rsplit("/in/", 1)[-1].lower()
        if first in slug and last in slug:
            return url
    return None


def _match_personal_email(name: str, emails: list[str], generic: list[str]) -> str | None:
    """first.last@ / flast@ / first@ patterns against public emails found on the site."""
    parts = [p for p in name.lower().replace(".", " ").split() if p.isalpha()]
    if not parts:
        return None
    first, last = parts[0], parts[-1]
    candidates = {f"{first}.{last}", f"{first}{last}", f"{first[0]}{last}", f"{first}_{last}", first, f"{first}.{last[0]}"}
    for email in emails:
        local = email.split("@", 1)[0]
        if local in candidates and not is_generic_mailbox(email, generic):
            return email
    return None


def choose_contact(snapshot: SiteSnapshot, campaign: CampaignConfig, defaults: DefaultRules,
                   company_domain: str | None = None) -> Contact:
    """Return the best contact. If no named decision-maker is public, fall back to the
    company's business mailbox so the lead stays actionable (flagged as generic)."""
    emails = usable_emails(snapshot.emails, company_domain, snapshot.source_emails) if company_domain else snapshot.emails
    best: tuple[int, str, str] | None = None
    for name, role in snapshot.team:
        rank = role_rank(role, campaign, defaults)
        if rank <= 0:
            continue
        if best is None or rank > best[0]:
            best = (rank, name, role)

    social = snapshot.social
    profile = social.get("linkedin")
    source_url = snapshot.pages["team"].url if "team" in snapshot.pages else (
        snapshot.pages["about"].url if "about" in snapshot.pages else snapshot.final_url)

    phone = best_phone(snapshot.phones)
    phone_kw = {"phone": phone.raw if phone else None, "phone_type": phone.kind if phone else None}

    if best:
        _, name, role = best
        personal = _match_personal_email(name, emails, defaults.generic_email_prefixes)
        fallback = next((e for e in emails), None)
        chosen = personal or fallback
        # Prefer the decision-maker's own LinkedIn over the company page when we can match it.
        person_profile = _match_personal_profile(name, snapshot.profiles) or profile
        return Contact(
            name=name, role=role, email=chosen,
            email_status=EmailStatus.UNVERIFIED if chosen else EmailStatus.NONE,
            email_source=_email_source(chosen, snapshot, personal is not None),
            profile_url=person_profile, source_url=source_url, is_decision_maker=True,
            evidence=f"'{name}' listed as '{role}' on {source_url}", **phone_kw,
        )

    business_email = next((e for e in emails), None)
    return Contact(
        name=None, role=None, email=business_email,
        email_status=EmailStatus.UNVERIFIED if business_email else EmailStatus.NONE,
        email_source=_email_source(business_email, snapshot, False),
        profile_url=profile, source_url=source_url, is_decision_maker=False,
        evidence="no named decision-maker published; business mailbox only" if business_email
                 else "no public contact found", **phone_kw,
    )


def _email_source(email: str | None, snapshot: SiteSnapshot, matched_to_name: bool) -> str | None:
    """Which page published this address (provenance for the reviewer)."""
    if not email:
        return None
    for kind, page in snapshot.pages.items():
        if email in page.emails:
            how = "matches contact name" if matched_to_name else "published"
            return f"{kind} page ({how}): {page.url}"
        if email in page.source_emails:
            return f"{kind} page source: {page.url}"
    return "website"
