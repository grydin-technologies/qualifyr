"""Phase C: multi-mailbox rotation."""

from datetime import timedelta

import pytest

from gtm_engine.models import CompanyType, EmailStatus, Lead, Priority, SequenceStatus
from gtm_engine.outreach.config import OutreachSettings, load_templates
from gtm_engine.outreach.ledger import Ledger
from gtm_engine.outreach.mailboxes import Mailbox, MailboxPool, load_mailboxes
from gtm_engine.outreach.sender import OutgoingEmail, SendResult
from gtm_engine.outreach.sequencer import enqueue, send_due, stop_lead
from gtm_engine.storage.database import Database
from test_outreach import MON_10AM_PKT


class RecordingSender:
    def __init__(self, address: str):
        self.from_addr = address
        self.name = f"fake:{address}"
        self.sent: list[OutgoingEmail] = []

    def send(self, email: OutgoingEmail) -> SendResult:
        self.sent.append(email)
        return SendResult(ok=True, message_id=f"<{email.lead_id}.{email.step}@{self.from_addr}>")


def _pool(settings, addresses, limits=None):
    boxes = [Mailbox(address=a, password="x", daily_limit=(limits or {}).get(a)) for a in addresses]
    senders: dict[str, RecordingSender] = {}
    pool = MailboxPool(boxes, settings, outbox=None, sender_factory=lambda box, dry: senders.setdefault(box.address, RecordingSender(box.address)))
    return pool, senders


def _leads(n: int) -> list[Lead]:
    return [Lead(campaign_id="test-retail", company_name=f"Co {i}", domain=f"co{i}.pk", city="Islamabad",
                 company_type=CompanyType.BUYER, total_score=90, priority=Priority.HIGH,
                 contact_email=f"owner@co{i}.pk", email_status=EmailStatus.MX_VALID, outreach_ready=True)
            for i in range(n)]


@pytest.fixture
def db(settings, campaign):
    d = Database(settings.database_url)
    d.upsert_campaign(campaign.campaign_id, campaign.name, campaign.model_dump(mode="json"))
    for l in _leads(10):
        d.save_lead(l, "run", l.domain)
    yield d
    d.close()


@pytest.fixture
def osettings():
    return OutreachSettings(daily_limit=4, warmup_enabled=False, jitter_min_s=0, jitter_max_s=0,
                            require_approval=False, followup_1_after_days=3, followup_2_after_days=4,
                            max_bounce_rate=0.10, min_sends_for_bounce_rate=2)


# --- env loading --------------------------------------------------------------------------

def test_load_numbered_mailboxes_and_legacy_fallback():
    env = {"GTM_MAILBOX_1_USER": "A@gmail.com", "GTM_MAILBOX_1_PASSWORD": "p1", "GTM_MAILBOX_1_LIMIT": "20",
           "GTM_MAILBOX_2_USER": "b@gmail.com", "GTM_MAILBOX_2_CLIENT_ID": "c", "GTM_MAILBOX_2_CLIENT_SECRET": "s",
           "GTM_MAILBOX_2_REFRESH_TOKEN": "r", "GTM_MAILBOX_2_NAME": "Sales Team",
           "GTM_MAILBOX_3_USER": "c@gmail.com", "GTM_MAILBOX_3_ENABLED": "false",
           "GTM_SMTP_USER": "ignored@gmail.com", "GTM_SMTP_PASSWORD": "zzz"}
    boxes = load_mailboxes(env)
    assert [b.address for b in boxes] == ["a@gmail.com", "b@gmail.com", "c@gmail.com"]  # legacy ignored when slot 1 is numbered
    assert boxes[0].auth_mode == "app_password" and boxes[0].daily_limit == 20
    assert boxes[1].auth_mode == "oauth2" and boxes[1].sender_name == "Sales Team"
    assert boxes[2].enabled is False and boxes[2].auth_mode == "none"
    legacy = load_mailboxes({"GTM_SMTP_USER": "me@gmail.com", "GTM_SMTP_PASSWORD": "p"})
    assert len(legacy) == 1 and legacy[0].address == "me@gmail.com" and legacy[0].can_send
    assert load_mailboxes({}) == []
    # The user's real layout: legacy vars as #1 plus GTM_MAILBOX_2_* – both must load, in order.
    mixed = load_mailboxes({"GTM_SMTP_USER": "me@gmail.com", "GTM_SMTP_PASSWORD": "p",
                            "GTM_MAILBOX_2_USER": "second@gmail.com", "GTM_MAILBOX_2_PASSWORD": "q"})
    assert [b.address for b in mixed] == ["me@gmail.com", "second@gmail.com"] and all(b.can_send for b in mixed)
    # Gaps allowed; duplicates collapse
    gap = load_mailboxes({"GTM_MAILBOX_1_USER": "a@gmail.com", "GTM_MAILBOX_1_PASSWORD": "p",
                          "GTM_MAILBOX_3_USER": "c@gmail.com", "GTM_MAILBOX_3_PASSWORD": "p",
                          "GTM_SMTP_USER": "a@gmail.com"})
    assert [b.address for b in gap] == ["a@gmail.com", "c@gmail.com"]


def test_settings_auth_mode_reflects_all_mailboxes(monkeypatch):
    for k in list(__import__("os").environ):
        if k.startswith("GTM_"):
            monkeypatch.delenv(k)
    monkeypatch.setenv("GTM_MAILBOX_1_USER", "a@gmail.com"); monkeypatch.setenv("GTM_MAILBOX_1_PASSWORD", "p")
    monkeypatch.setenv("GTM_MAILBOX_2_USER", "b@gmail.com"); monkeypatch.setenv("GTM_MAILBOX_2_CLIENT_ID", "c")
    monkeypatch.setenv("GTM_MAILBOX_2_CLIENT_SECRET", "s"); monkeypatch.setenv("GTM_MAILBOX_2_REFRESH_TOKEN", "r")
    s = OutreachSettings()
    assert s.credentials_present and s.auth_mode == "mixed" and s.smtp_user == "a@gmail.com"


# --- rotation -------------------------------------------------------------------------------

def test_email_1_rotates_to_least_loaded_mailbox(db, campaign, osettings, tmp_path):
    ledger = Ledger(tmp_path / "l.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    pool, senders = _pool(osettings, ["a@gmail.com", "b@gmail.com"])
    r = send_due(db, campaign, osettings, load_templates(), pool, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 8 and "daily limit reached" in r.stopped_reason
    assert len(senders["a@gmail.com"].sent) == 4 and len(senders["b@gmail.com"].sent) == 4
    # alternation: a, b, a, b ... (least-loaded, ties by address)
    order = [d.split(" via ")[1] for d in r.details if " via " in d]
    assert order[:4] == ["a@gmail.com", "b@gmail.com", "a@gmail.com", "b@gmail.com"]
    assert ledger.sent_on(MON_10AM_PKT.strftime("%Y-%m-%d"), "a@gmail.com") == 4
    assert r.mailboxes["b@gmail.com"]["remaining"] == 0
    # leads remember their mailbox
    assert {l.mailbox for l in db.list_leads("test-retail") if l.sequence_status == SequenceStatus.EMAIL_1_SENT} == {"a@gmail.com", "b@gmail.com"}


def test_per_mailbox_limit_and_warmup_are_independent(db, campaign, osettings, tmp_path):
    osettings.warmup_enabled = True
    osettings.warmup_start_per_day = 2
    osettings.warmup_step_per_day = 10
    ledger = Ledger(tmp_path / "l.json")
    ledger.note_send_day("a@gmail.com", (MON_10AM_PKT - timedelta(days=5)).strftime("%Y-%m-%d"))  # veteran: full cap
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    pool, senders = _pool(osettings, ["a@gmail.com", "b@gmail.com"], limits={"a@gmail.com": 3})
    r = send_due(db, campaign, osettings, load_templates(), pool, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert len(senders["a@gmail.com"].sent) == 3   # per-mailbox limit 3 beats cap 4
    assert len(senders["b@gmail.com"].sent) == 2   # brand new: warm-up day 1 = 2
    assert r.mailboxes["b@gmail.com"]["days_active"] is None or r.mailboxes["b@gmail.com"]["cap"] == 2


def test_followups_stay_on_originating_mailbox(db, campaign, osettings, tmp_path):
    ledger = Ledger(tmp_path / "l.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    pool, senders = _pool(osettings, ["a@gmail.com", "b@gmail.com"])
    send_due(db, campaign, osettings, load_templates(), pool, ledger, limit=4, now=MON_10AM_PKT, sleep=lambda s: None)
    owners = {l.contact_email: l.mailbox for l in db.list_leads("test-retail") if l.mailbox}
    day3 = MON_10AM_PKT + timedelta(days=3)
    r = send_due(db, campaign, osettings, load_templates(), pool, ledger, limit=4, now=day3, sleep=lambda s: None)
    fu = [e for s in senders.values() for e in s.sent if e.step == "followup_1"]
    assert len(fu) == 4 and r.sent == 4
    for s in senders.values():
        for e in s.sent:
            if e.step == "followup_1":
                assert owners[e.to] == s.from_addr, f"{e.to} follow-up left from the wrong mailbox"
                assert e.in_reply_to and e.in_reply_to.endswith(f"@{s.from_addr}>")


def test_paused_mailbox_holds_its_followups_only(db, campaign, osettings, tmp_path):
    ledger = Ledger(tmp_path / "l.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    pool, senders = _pool(osettings, ["a@gmail.com", "b@gmail.com"])
    send_due(db, campaign, osettings, load_templates(), pool, ledger, limit=4, now=MON_10AM_PKT, sleep=lambda s: None)
    # day 3: two of a's threads bounce -> a is paused for today; b is fine
    day3 = MON_10AM_PKT + timedelta(days=3)
    a_leads = [l for l in db.list_leads("test-retail") if l.mailbox == "a@gmail.com"]
    for l in a_leads:
        l.last_sent_at = day3          # bounce counted against today's sends from a
        db.update_lead(l)
    ledger.record_sent(a_leads[0].contact_email, "x", None, "x", day3, mailbox="a@gmail.com")
    ledger.record_sent(a_leads[1].contact_email, "y", None, "y", day3, mailbox="a@gmail.com")
    for l in a_leads:
        stop_lead(db, l, SequenceStatus.BOUNCED, "bounce", ledger)
    r = send_due(db, campaign, osettings, load_templates(), pool, ledger, now=day3, sleep=lambda s: None)
    assert r.mailboxes["a@gmail.com"]["paused_reason"] and not r.mailboxes["b@gmail.com"]["paused_reason"]
    b_followups = [e for e in senders["b@gmail.com"].sent if e.step == "followup_1"]
    assert len(b_followups) == 2 and r.sent >= 2
    assert not any(e.step == "followup_1" for e in senders["a@gmail.com"].sent)


def test_pool_without_credentials_is_dry_run(settings, osettings, tmp_path):
    pool = MailboxPool([], osettings, outbox=tmp_path / "outbox")
    assert pool.dry_run and pool.name == "dry-run" and pool.addresses() == ["dryrun@example.invalid"]
    s = pool.sender_for("dryrun@example.invalid")
    assert s.send(OutgoingEmail(to="a@b.pk", subject="s", body="b", lead_id="l", step="email_1")).ok


def test_legacy_untagged_sends_belong_only_to_first_mailbox(tmp_path, osettings, settings, campaign):
    ledger = Ledger(tmp_path / "l.json")
    ledger.record_sent("x@co.pk", "email_1", "<m>", "l1")
    ledger.data["sent"]["x@co.pk"]["email_1"]["at"] = "2027-02-20T05:00:00+00:00"
    del ledger.data["sent"]["x@co.pk"]["email_1"]["mailbox"]
    db = Database(settings.database_url)
    db.upsert_campaign(campaign.campaign_id, campaign.name, campaign.model_dump(mode="json"))
    pool, _ = _pool(osettings, ["old@gmail.com", "new@gmail.com"])
    states = pool.states(db, "test-retail", ledger, "2027-03-01")
    assert states["old@gmail.com"].days_active == 10
    assert states["new@gmail.com"].days_active is None
    db.close()
