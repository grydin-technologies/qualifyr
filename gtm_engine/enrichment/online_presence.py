"""Online-presence / digital-maturity audit for a business.

Detects: e-commerce capability, mobile app, WhatsApp ordering, social presence,
delivery-platform listings. The inverse (high business potential + low digital
maturity) is the ranking signal that makes prospects winnable."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus

from gtm_engine.models import OnlinePresence
from gtm_engine.scraping.site_crawler import SiteSnapshot

log = logging.getLogger(__name__)

# ── e-commerce detection ────────────────────────────────────────────────

_CART_SIGNALS = re.compile(
    r"add[- _]?to[- _]?cart|add[- _]?to[- _]?basket|buy[- _]?now|checkout|"
    r"shopping[- _]?cart|proceed[- _]?to[- _]?payment|place[- _]?order|"
    r"view[- _]?cart|cart[- _]?total|your[- _]?bag|woocommerce|shopify|"
    r"snipcart|ecwid|bigcommerce",
    re.I,
)

_ECOMMERCE_PLATFORMS: dict[str, re.Pattern] = {
    "shopify": re.compile(r"cdn\.shopify\.com|Shopify\.theme|myshopify\.com", re.I),
    "woocommerce": re.compile(r"woocommerce|wc-add-to-cart|wc-cart", re.I),
    "magento": re.compile(r"Magento|mage/cookies", re.I),
    "opencart": re.compile(r"catalog/view/theme|route=product", re.I),
    "prestashop": re.compile(r"prestashop|modules/ps_", re.I),
}

# ── delivery platforms (Pakistan-focused) ────────────────────────────────

DELIVERY_PLATFORMS = {
    "foodpanda": re.compile(r"foodpanda\.pk", re.I),
    "daraz": re.compile(r"daraz\.pk", re.I),
    "bykea": re.compile(r"bykea\.com", re.I),
    "careem": re.compile(r"careem\.com", re.I),
    "yango": re.compile(r"yango\.(com|pk)", re.I),
    "cheetay": re.compile(r"cheetay\.pk", re.I),
    "golootlo": re.compile(r"golootlo\.com", re.I),
}


def _detect_ecommerce(snapshot: SiteSnapshot) -> tuple[bool, bool, str | None]:
    """Returns (has_ecommerce_site, has_cart, ecommerce_platform)."""
    if not snapshot.reachable:
        return False, False, None
    html_blob = " ".join(snapshot.raw_html.values())
    platform: str | None = None
    for name, pattern in _ECOMMERCE_PLATFORMS.items():
        if pattern.search(html_blob):
            platform = name
            break
    has_cart = bool(_CART_SIGNALS.search(html_blob))
    has_ecommerce = has_cart or platform is not None
    return has_ecommerce, has_cart, platform


def _detect_whatsapp(snapshot: SiteSnapshot) -> tuple[bool, str | None]:
    """Detects WhatsApp ordering links from crawled pages."""
    wa_re = re.compile(r"wa\.me/\+?(\d+)|api\.whatsapp\.com/send\?phone=\+?(\d+)", re.I)
    for page in snapshot.pages.values():
        for raw in (snapshot.raw_html.get(kind, "") for kind in snapshot.pages):
            m = wa_re.search(raw)
            if m:
                number = m.group(1) or m.group(2)
                return True, number
    return False, None


def _detect_social(snapshot: SiteSnapshot) -> dict[str, str | None]:
    """Extract Facebook and Instagram URLs from parsed social links."""
    social: dict[str, str | None] = {"facebook": None, "instagram": None}
    for page in snapshot.pages.values():
        if page.social.get("facebook") and not social["facebook"]:
            social["facebook"] = page.social["facebook"]
        if page.social.get("instagram") and not social["instagram"]:
            social["instagram"] = page.social["instagram"]
    return social


def _detect_delivery_platforms(snapshot: SiteSnapshot) -> list[str]:
    """Check if the site links to or mentions known delivery platforms."""
    if not snapshot.reachable:
        return []
    text = snapshot.all_text.lower()
    html_blob = " ".join(snapshot.raw_html.values()).lower()
    combined = text + " " + html_blob
    found: list[str] = []
    for name, pattern in DELIVERY_PLATFORMS.items():
        if pattern.search(combined):
            found.append(name)
    return found


def _infer_delivery_model(
    has_ecommerce: bool,
    delivery_platforms: list[str],
    has_whatsapp: bool,
    snapshot: SiteSnapshot,
) -> str:
    """Infer how the business currently handles delivery/ordering."""
    if not snapshot.reachable:
        return "unknown"
    text = snapshot.all_text.lower()
    own_delivery = bool(re.search(
        r"our\s+deliver|we\s+deliver|own\s+rider|home\s+deliver|free\s+deliver|delivery\s+service",
        text,
    ))
    if has_ecommerce and own_delivery:
        return "own"
    if has_ecommerce and delivery_platforms:
        return "hybrid"
    if delivery_platforms and not has_ecommerce:
        return "third_party"
    if has_whatsapp and not has_ecommerce:
        return "phone_only"
    phone_order = bool(re.search(r"call\s+to\s+order|order\s+by\s+phone|phone\s+order", text))
    if phone_order:
        return "phone_only"
    return "none"


def _compute_online_gap(presence: OnlinePresence) -> int:
    """0-25 score: higher = bigger digital gap = better prospect for a tech solution.
    Mirrors the reverse-engineered formula from the reference xlsx."""
    gap = 22  # start high (no ordering channel)
    if presence.has_ecommerce_site and presence.has_cart:
        gap -= 12
    elif presence.has_ecommerce_site:
        gap -= 8
    if presence.has_mobile_app:
        gap -= 6
    if presence.delivery_platforms:
        gap -= min(len(presence.delivery_platforms) * 2, 6)
    if presence.has_whatsapp_ordering:
        gap -= 2
    if presence.has_facebook or presence.has_instagram:
        gap -= 1
    if presence.google_review_count and presence.google_review_count > 50:
        gap -= 1
    return max(0, gap)


def audit_online_presence(
    snapshot: SiteSnapshot,
    company_name: str | None = None,
    technologies: list[str] | None = None,
) -> OnlinePresence:
    """Run the full online-presence audit from a crawled site snapshot."""
    has_ecommerce, has_cart, ecommerce_platform = _detect_ecommerce(snapshot)

    # Merge platform detection from the existing technology markers
    if technologies and not ecommerce_platform:
        for tech in technologies:
            if tech in ("shopify", "woocommerce", "magento", "opencart", "prestashop"):
                ecommerce_platform = tech
                has_ecommerce = True
                break

    has_whatsapp, whatsapp_number = _detect_whatsapp(snapshot)
    social = _detect_social(snapshot)
    delivery_platforms = _detect_delivery_platforms(snapshot)
    delivery_model = _infer_delivery_model(has_ecommerce, delivery_platforms, has_whatsapp, snapshot)

    notes: list[str] = []
    if not snapshot.reachable:
        notes.append("website unreachable – online presence could not be fully audited")
    if has_ecommerce and not has_cart:
        notes.append("e-commerce platform detected but no cart/checkout flow found")
    if delivery_model == "none" and not has_whatsapp:
        notes.append("no online ordering channel detected")

    presence = OnlinePresence(
        has_ecommerce_site=has_ecommerce,
        has_cart=has_cart,
        ecommerce_platform=ecommerce_platform,
        has_mobile_app=False,  # filled by pipeline via search (not from site HTML alone)
        has_whatsapp_ordering=has_whatsapp,
        whatsapp_number=whatsapp_number,
        has_facebook=bool(social["facebook"]),
        facebook_url=social["facebook"],
        has_instagram=bool(social["instagram"]),
        instagram_url=social["instagram"],
        delivery_platforms=delivery_platforms,
        delivery_model=delivery_model,
        notes=notes,
    )
    presence.online_gap_score = _compute_online_gap(presence)
    return presence


def online_gap_labels(op: OnlinePresence) -> list[str]:
    """Named gaps for the pitch-angle generator – what's missing from this business's digital setup."""
    gaps: list[str] = []
    if not op.has_ecommerce_site:
        gaps.append("no_ecommerce")
    elif not op.has_cart:
        gaps.append("no_cart")
    if not op.has_whatsapp_ordering:
        gaps.append("no_whatsapp_ordering")
    if not op.delivery_platforms:
        gaps.append("no_delivery_platform")
    if not op.has_mobile_app:
        gaps.append("no_mobile_app")
    if not op.has_facebook and not op.has_instagram:
        gaps.append("no_social")
    if op.google_place_id and op.google_review_count is not None and op.google_review_count < 10:
        gaps.append("low_google_visibility")
    if op.pain_from_reviews:
        gaps.append("review_complaints")
    return gaps
