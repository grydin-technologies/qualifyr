"""Core data models shared by every stage. Each stage adds fields; nothing is dropped,
so a lead's evidence trail survives to the CSV."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class CompanyType(str, Enum):
    BUYER = "BUYER"
    VENDOR = "VENDOR"
    UNKNOWN = "UNKNOWN"


class EmailStatus(str, Enum):
    NONE = "none"                 # no email found
    INVALID = "invalid"           # failed syntax or domain has no MX
    UNVERIFIED = "unverified"     # syntax ok, MX not checked yet
    MX_VALID = "mx_valid"         # syntax ok and domain accepts mail
    GENERIC = "generic"           # role mailbox (info@, sales@) with valid MX
    DELIVERABLE = "deliverable"   # mailbox confirmed by an SMTP-level verifier
    RISKY = "risky"               # catch-all domain / verifier unsure: never for discovered addresses
    CANDIDATE = "candidate"       # pattern-discovered, no verifier available: shown, never sent
    BOUNCED = "bounced"


class SequenceStatus(str, Enum):
    NOT_QUEUED = "not_queued"
    QUEUED = "queued"
    EMAIL_1_SENT = "email_1_sent"
    FOLLOWUP_1_SENT = "followup_1_sent"
    FOLLOWUP_2_SENT = "followup_2_sent"
    COMPLETED = "completed"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    SUPPRESSED = "suppressed"


class Priority(str, Enum):
    HIGH = "high_priority"
    QUALIFIED = "qualified"
    REVIEW = "review"
    REJECT = "reject"


class DiscoveredCompany(BaseModel):
    """Output of a discovery source. Only what the source can honestly provide."""

    name: str
    website: str | None = None
    domain: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    category: str | None = None
    source: str
    source_url: str | None = None
    extra: dict = Field(default_factory=dict)


class ScrapedPage(BaseModel):
    url: str
    kind: str  # home | about | contact | team | services | other
    status_code: int
    title: str | None = None
    text: str = ""
    html: str = ""
    fetched_at: datetime = Field(default_factory=utcnow)


class Contact(BaseModel):
    name: str | None = None
    role: str | None = None
    email: str | None = None
    email_status: EmailStatus = EmailStatus.NONE
    phone: str | None = None
    profile_url: str | None = None
    source_url: str | None = None
    is_decision_maker: bool = False
    evidence: str | None = None
    email_source: str | None = None      # provenance: where the address came from
    email_pattern: str | None = None     # first.last etc. when discovered
    phone_type: str | None = None        # mobile | landline | unknown
    candidate_email: str | None = None   # discovered but unconfirmed address, for the reviewer


class Classification(BaseModel):
    company_type: CompanyType
    confidence: float = 0.0  # 0..1
    reasons: list[str] = Field(default_factory=list)
    buyer_hits: list[str] = Field(default_factory=list)
    vendor_hits: list[str] = Field(default_factory=list)
    # LLM intent judgment (None when the LLM is off): does this company plausibly NEED the
    # offer, judged from its own text rather than keyword hits. Drives the type and the score.
    intent_buyer: bool | None = None
    intent_confidence: float = 0.0
    intent_reason: str = ""


class Signals(BaseModel):
    buying: dict[str, list[str]] = Field(default_factory=dict)
    pain: dict[str, list[str]] = Field(default_factory=dict)
    technologies: list[str] = Field(default_factory=list)
    news: list[dict] = Field(default_factory=list)          # [{title,url,date,source}]
    intent: list[dict] = Field(default_factory=list)        # IntentSignal dicts
    domain_age_years: float | None = None
    domain_age_note: str | None = None
    # GTM intelligence: open roles on Greenhouse/Lever, GitHub org activity, press/RSS hits.
    job_openings: list[dict] = Field(default_factory=list)      # [{title,location,url,board,growth_role}]
    github_activity: dict | None = None                          # {org,url,public_repos,last_pushed_at,stars_total}
    press_mentions: list[dict] = Field(default_factory=list)    # [{title,url,date,kind}]


class OnlinePresence(BaseModel):
    """Digital-maturity audit: what ordering/delivery channels a business has.
    The inverse (high potential + low digital maturity) is the core ranking signal."""

    has_ecommerce_site: bool = False
    has_cart: bool = False
    ecommerce_platform: str | None = None          # shopify / woocommerce / custom / None
    has_mobile_app: bool = False
    app_store_url: str | None = None
    has_whatsapp_ordering: bool = False
    whatsapp_number: str | None = None
    has_facebook: bool = False
    facebook_url: str | None = None
    has_instagram: bool = False
    instagram_url: str | None = None
    delivery_platforms: list[str] = Field(default_factory=list)  # foodpanda, daraz, bykea, ...
    delivery_model: str | None = None               # none / own / third_party / phone_only
    google_rating: float | None = None              # 1.0-5.0 from Google Places
    google_review_count: int | None = None
    google_place_id: str | None = None
    opening_hours_raw: str | None = None            # OSM-format opening hours string
    opening_hours_days: int | None = None            # days per week the business is open
    pain_from_reviews: list[str] = Field(default_factory=list)  # pain signals mined from Google review text
    online_gap_score: int = 0                        # 0-25: higher = bigger gap = better prospect
    notes: list[str] = Field(default_factory=list)


class CompanyQuality(BaseModel):
    reachable: bool = False
    https: bool = False
    has_contact_page: bool = False
    has_about_page: bool = False
    has_public_email: bool = False
    has_phone: bool = False
    page_count: int = 0
    website_mismatch: bool = False
    copyright_year: int | None = None
    mobile_friendly: bool | None = None
    notes: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """Decomposed transparent score (reference xlsx formula)."""

    review_band: int = 0       # 0-30: Google review count bands
    rating_score: int = 0      # 0-10: Google rating scaled
    proximity_tier: int = 0    # 0-15: distance from anchor (15/12/8/0)
    online_gap: int = 0        # 0-25: inverse digital maturity
    pain_evidence: int = 0     # 0-20: pain signals from reviews + site
    total: int = 0
    reasons: list[str] = Field(default_factory=list)
    priority: Priority = Priority.REJECT


class Lead(BaseModel):
    """One qualified (or rejected) company-level lead. Maps 1:1 to the CSV schema."""

    lead_id: str = Field(default_factory=lambda: new_id("lead"))
    campaign_id: str
    company_name: str
    domain: str | None = None
    website: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    industry: str | None = None
    company_description: str | None = None
    company_type: CompanyType = CompanyType.UNKNOWN
    buyer_fit_score: int = 0
    buyer_fit_reason: str = ""
    company_quality_score: int = 0
    buying_signal_score: int = 0
    total_score: int = 0
    score_reason: str = ""
    contact_name: str | None = None
    contact_role: str | None = None
    contact_email: str | None = None
    email_status: EmailStatus = EmailStatus.NONE
    phone: str | None = None
    linkedin_or_public_profile_url: str | None = None
    pain_signal: str | None = None
    buying_signal: str | None = None
    personalization_hook: str | None = None
    research_brief: str | None = None    # consolidated per-company research summary (P5)
    online_presence: dict | None = None  # OnlinePresence.model_dump() – digital-maturity audit
    pitch_angle: str | None = None       # module→pain pitch (specific to this lead's gaps)
    # LLM intent verdict: whether the company plausibly NEEDS the offer, judged from its own
    # text (not keywords). None when the LLM layer is off. Surfaced in the UI and CSV-adjacent.
    intent_fit: bool | None = None
    intent_confidence: float = 0.0
    intent_reason: str = ""
    source: str = ""
    source_url: str | None = None
    scraped_at: datetime = Field(default_factory=utcnow)
    outreach_ready: bool = False
    sequence_status: SequenceStatus = SequenceStatus.NOT_QUEUED
    email_1_sent_at: datetime | None = None
    followup_1_at: datetime | None = None
    followup_2_at: datetime | None = None
    reply_status: str | None = None
    priority: Priority = Priority.REJECT
    technologies: list[str] = Field(default_factory=list)
    evidence: dict = Field(default_factory=dict)
    phone_type: str | None = None
    candidate_email: str | None = None
    news_mentions: list[dict] = Field(default_factory=list)
    domain_age_years: float | None = None
    intent_signals: list[dict] = Field(default_factory=list)   # IntentSignal dicts
    job_openings: list[dict] = Field(default_factory=list)
    github_activity: dict | None = None
    press_mentions: list[dict] = Field(default_factory=list)
    review_verdict: str | None = None       # correct | wrong_company | wrong_person | wrong_email (human)
    reviewed_at: datetime | None = None
    # Which source produced each important field: {"contact_email": "contact page mailto", ...}
    provenance: dict[str, str] = Field(default_factory=dict)
    # Outreach state (not in the CSV schema, kept in the DB and the ledger)
    approved: bool = False
    next_contact_at: datetime | None = None
    thread_message_id: str | None = None   # Message-ID of email 1; follow-ups reply to it
    mailbox: str | None = None             # address that sent email 1; follow-ups use the same one
    reply_label: str | None = None         # interested | not_interested | out_of_office | wrong_person | unsubscribe | auto_reply | reply
    reply_excerpt: str | None = None       # first lines of the fresh reply text, for the reviewer
    referred_contact: dict | None = None   # {"name": ..., "email": ...} when the lead pointed us elsewhere
    last_sent_at: datetime | None = None


CSV_COLUMNS: list[str] = [
    "lead_id", "campaign_id", "company_name", "domain", "website", "country", "city",
    "address", "industry", "company_description", "company_type", "buyer_fit_score",
    "buyer_fit_reason", "company_quality_score", "buying_signal_score", "total_score",
    "score_reason", "contact_name", "contact_role", "contact_email", "email_status",
    "phone", "linkedin_or_public_profile_url", "pain_signal", "buying_signal",
    "personalization_hook", "source", "source_url", "scraped_at", "outreach_ready",
    "sequence_status", "email_1_sent_at", "followup_1_at", "followup_2_at", "reply_status",
]
