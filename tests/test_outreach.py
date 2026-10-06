from datetime import datetime, timedelta, timezone

import pytest

from gtm_engine.models import CompanyType, EmailStatus, Lead, Priority, SequenceStatus
from gtm_engine.outreach.config import OutreachSettings, load_templates
from gtm_engine.outreach.ledger import Ledger
from gtm_engine.outreach.reply_state import InboundMessage, apply_inbound
from gtm_engine.outreach.sender import DryRunSender, OutgoingEmail, SendResult, build_message
from gtm_engine.outreach.sequencer import due_leads, enqueue, in_send_window, send_due
from gtm_engine.outreach.templates import first_name, hook_sentence, render
from gtm_engine.storage.database import Database

MON_10AM_PKT = datetime(2027, 3, 1, 5, 0, tzinfo=timezone.utc)  # a Monday, 10:00 Asia/Karachi; fixed clock for the whole suite


@pytest.fixture
def osettings() -> OutreachSettings:
    return OutreachSettings(sender_name="Haseeb", daily_limit=3, delay_between_sends_s=0,
                            followup_1_after_days=3, followup_2_after_days=4, require_approval=False)


@pytest.fixture
def templates():
    return load_templates()


def _lead(name: str, email: str, **kw) -> Lead:
    base = dict(campaign_id="test-retail", company_name=name, domain=email.split("@")[1], city="Islamabad",
                company_type=CompanyType.BUYER, total_score=85, priority=Priority.HIGH,
                contact_email=email, email_status=EmailStatus.MX_VALID, outreach_ready=True,
                personalization_hook="based in Islamabad; sells online; runs on shopify")
    base.update(kw)
    return Lead(**base)


@pytest.fixture
def db(settings, campaign):
    d = Database(settings.database_url)
    d.upsert_campaign(campaign.campaign_id, campaign.name, campaign.model_dump(mode="json"))
    for l in (
        _lead("Zara Fabrics", "ahmed@zarafabrics.pk", contact_name="Ahmed Raza", total_score=92),
        _lead("Madina Cash & Carry", "info@mcc.com.pk", email_status=EmailStatus.GENERIC),
        _lead("Bakala", "x@bakala.store", email_status=EmailStatus.NONE, contact_email=None, outreach_ready=False),
        _lead("Pixel Digital", "hello@pixeldigital.pk", company_type=CompanyType.VENDOR, outreach_ready=False),
    ):
        d.save_lead(l, "run_test", l.domain)
    yield d
    d.close()


class FakeSender:
    name = "fake"

    def __init__(self, fail_for: set[str] = ()):
        self.sent: list[OutgoingEmail] = []
        self.fail_for = set(fail_for)

    def send(self, email: OutgoingEmail) -> SendResult:
        if email.to in self.fail_for:
            return SendResult(ok=False, message_id=None, error="recipient_refused:{...}")
        self.sent.append(email)
        return SendResult(ok=True, message_id=f"<{email.lead_id}.{email.step}@test>")


# --- templates ---------------------------------------------------------------------

def test_first_name_and_hook_sentence():
    assert first_name("Dr. Muhammad Usman Khan") == "Usman"
    assert first_name("Ahmed Raza") == "Ahmed"
    assert first_name(None) is None
    assert hook_sentence("based in Islamabad; sells online; runs on shopify") == \
        " I noticed you sell online and your store runs on shopify."
    assert hook_sentence("based in Islamabad") == ""
    assert hook_sentence(None) == ""


def test_render_uses_facts_and_fallbacks(campaign, osettings, templates):
    named = render("email_1", _lead("Zara Fabrics", "a@zarafabrics.pk", contact_name="Ahmed Raza"), campaign, osettings, templates)
    assert named.subject == "Zara Fabrics – quick question"
    assert named.body.startswith("Hi Ahmed,")
    assert "I noticed you sell online" in named.body
    assert "reply with STOP" in named.body
    assert named.missing == []

    anon = render("followup_2", _lead("MCC", "info@mcc.com.pk", personalization_hook=None, city=None), campaign, osettings, templates)
    assert anon.body.startswith("Hi there,")
    assert "I noticed" not in anon.body
    assert anon.subject.startswith("Re: ")
    assert set(anon.missing) == {"first_name", "city"}
    assert "{" not in anon.body  # no unfilled placeholders ever reach a recipient


def test_render_rejects_unknown_placeholder(campaign, osettings, templates):
    templates.email_1.body = "Hi {first_name}, {made_up_field}"
    with pytest.raises(ValueError):
        render("email_1", _lead("X", "x@x.pk"), campaign, osettings, templates)


# --- sender ---------------------------------------------------------------------------

def test_message_headers_thread_and_unsubscribe(osettings):
    msg = build_message(OutgoingEmail(to="a@b.pk", subject="S", body="B", in_reply_to="<root@x>", lead_id="lead_1", step="followup_1"),
                        osettings, "me@gmail.com")
    assert msg["In-Reply-To"] == "<root@x>" and msg["References"] == "<root@x>"
    assert msg["List-Unsubscribe"] == "<mailto:me@gmail.com?subject=STOP>"
    assert msg["Message-ID"].endswith("@gmail.com>")
    assert msg["From"] == "Haseeb <me@gmail.com>"


def test_dry_run_writes_eml(osettings, tmp_path):
    s = DryRunSender(osettings, tmp_path / "outbox")
    r = s.send(OutgoingEmail(to="a@b.pk", subject="S", body="B", lead_id="lead_1", step="email_1"))
    assert r.ok and (tmp_path / "outbox" / "lead_1_email_1.eml").exists()


# --- window ----------------------------------------------------------------------------

def test_send_window(osettings):
    assert in_send_window(MON_10AM_PKT, osettings)
    assert not in_send_window(MON_10AM_PKT + timedelta(hours=10), osettings)   # 20:00 PKT
    assert not in_send_window(MON_10AM_PKT - timedelta(days=1), osettings)     # Sunday


# --- sequence ---------------------------------------------------------------------------

def test_enqueue_only_gate_passers(db, osettings, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    queued = enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    assert sorted(l.company_name for l in queued) == ["Madina Cash & Carry", "Zara Fabrics"]
    assert enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT) == []  # idempotent


def test_full_sequence_with_delays_and_cap(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    sender = FakeSender()

    r1 = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r1.sent == 2 and [e.step for e in sender.sent] == ["email_1", "email_1"]
    zara = next(l for l in db.list_leads("test-retail") if l.company_name == "Zara Fabrics")
    assert zara.sequence_status == SequenceStatus.EMAIL_1_SENT
    assert zara.thread_message_id and zara.email_1_sent_at
    assert zara.next_contact_at == MON_10AM_PKT + timedelta(days=3)
    assert ledger.has_sent("ahmed@zarafabrics.pk", "email_1")

    # Nothing due the next day
    assert due_leads(db, "test-retail", MON_10AM_PKT + timedelta(days=1)) == []
    r2 = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT + timedelta(days=1), sleep=lambda s: None)
    assert r2.sent == 0

    # Follow-up 1 after 3 days, threaded on email 1
    day3 = MON_10AM_PKT + timedelta(days=3)
    r3 = send_due(db, campaign, osettings, templates, sender, ledger, now=day3, sleep=lambda s: None)
    assert r3.sent == 2
    fu = sender.sent[-1]
    assert fu.step == "followup_1" and fu.in_reply_to and fu.subject.startswith("Re: ")

    # Follow-up 2 after 4 more days, then done
    day7 = day3 + timedelta(days=4)
    r4 = send_due(db, campaign, osettings, templates, sender, ledger, now=day7, sleep=lambda s: None)
    assert r4.sent == 2
    zara = db.get_lead(zara.lead_id)
    assert zara.sequence_status == SequenceStatus.FOLLOWUP_2_SENT and zara.followup_2_at == day7
    assert due_leads(db, "test-retail", day7 + timedelta(days=30)) == []
    assert len(sender.sent) == 6


def test_daily_cap_and_window(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    osettings.daily_limit = 1
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    sender = FakeSender()
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 1 and "daily limit" in r.stopped_reason
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT + timedelta(hours=1), sleep=lambda s: None)
    assert r.sent == 0 and "daily limit" in r.stopped_reason
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT - timedelta(days=1), sleep=lambda s: None)
    assert r.sent == 0 and r.stopped_reason == "outside send window"


def test_ledger_prevents_double_send_after_db_loss(db, campaign, osettings, templates, tmp_path, pg_schema):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    send_due(db, campaign, osettings, templates, FakeSender(), ledger, now=MON_10AM_PKT, sleep=lambda s: None)

    # Simulate a fresh runner: brand-new DB with the leads re-scraped, same ledger file on disk.
    fresh = Database(pg_schema())
    fresh.upsert_campaign(campaign.campaign_id, campaign.name, campaign.model_dump(mode="json"))
    for l in db.list_leads("test-retail"):
        l.sequence_status = SequenceStatus.NOT_QUEUED
        l.thread_message_id = None
        fresh.save_lead(l, "run_2", l.domain)
    ledger2 = Ledger(tmp_path / "ledger.json")
    assert enqueue(fresh, "test-retail", osettings, ledger2, now=MON_10AM_PKT) == []
    zara = next(l for l in fresh.list_leads("test-retail") if l.company_name == "Zara Fabrics")
    assert zara.sequence_status == SequenceStatus.EMAIL_1_SENT
    assert zara.thread_message_id.endswith(".email_1@test>")
    sender = FakeSender()
    send_due(fresh, campaign, osettings, templates, sender, ledger2, now=MON_10AM_PKT + timedelta(hours=1), sleep=lambda s: None)
    assert sender.sent == []  # follow-up not due yet, email 1 never repeated
    fresh.close()


def test_bounce_on_send_stops_and_suppresses(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    sender = FakeSender(fail_for={"info@mcc.com.pk"})
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 1 and r.failed == 1
    mcc = next(l for l in db.list_leads("test-retail") if l.company_name == "Madina Cash & Carry")
    assert mcc.sequence_status == SequenceStatus.BOUNCED and not mcc.outreach_ready
    assert db.is_suppressed("info@mcc.com.pk") and ledger.is_stopped("info@mcc.com.pk")


def test_suppression_added_mid_sequence_stops_followups(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    sender = FakeSender()
    send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    db.add_suppression("zarafabrics.pk", "domain", "asked by phone")
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT + timedelta(days=3), sleep=lambda s: None)
    assert r.sent == 1 and r.skipped == 1
    assert all(e.to != "ahmed@zarafabrics.pk" for e in sender.sent[2:])


# --- replies ------------------------------------------------------------------------------

def test_inbound_reply_stop_and_bounce(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    send_due(db, campaign, osettings, templates, FakeSender(), ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    zara = next(l for l in db.list_leads("test-retail") if l.company_name == "Zara Fabrics")

    report = apply_inbound(db, "test-retail", [
        InboundMessage(from_addr="someone-else@zarafabrics.pk", subject="Re: Zara Fabrics – quick question",
                       body="Sure, let's talk Thursday.", in_reply_to=zara.thread_message_id),
        InboundMessage(from_addr="info@mcc.com.pk", subject="Re: ...", body="Please STOP emailing us."),
        InboundMessage(from_addr="mailer-daemon@googlemail.com", subject="Delivery Status Notification (Failure)",
                       body="The address info@mcc.com.pk could not be found"),
        InboundMessage(from_addr="newsletter@random.com", subject="Weekly deals", body="unsubscribe here"),
    ], ledger)
    assert (report.replied, report.unsubscribed, report.bounced) == (1, 1, 0)  # mcc already stopped by STOP
    leads = {l.company_name: l for l in db.list_leads("test-retail")}
    assert leads["Zara Fabrics"].sequence_status == SequenceStatus.REPLIED
    assert leads["Zara Fabrics"].reply_label == "interested" and leads["Zara Fabrics"].reply_status.startswith("interested:")
    assert leads["Madina Cash & Carry"].sequence_status == SequenceStatus.UNSUBSCRIBED
    assert db.is_suppressed("info@mcc.com.pk")
    # Neither gets any further email
    r = send_due(db, campaign, osettings, templates, FakeSender(), ledger, now=MON_10AM_PKT + timedelta(days=3), sleep=lambda s: None)
    assert r.sent == 0


def test_bounce_quoting_our_thread_is_bounce_not_reply(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    send_due(db, campaign, osettings, templates, FakeSender(), ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    zara = next(l for l in db.list_leads("test-retail") if l.company_name == "Zara Fabrics")
    bounce = InboundMessage(from_addr="mailer-daemon@googlemail.com", subject="Delivery Status Notification (Failure)",
                            body="Your message wasn't delivered to ahmed@zarafabrics.pk because the address couldn't be found",
                            in_reply_to=zara.thread_message_id, references=zara.thread_message_id)
    report = apply_inbound(db, "test-retail", [bounce], ledger)
    assert (report.replied, report.bounced) == (0, 1)
    zara = db.get_lead(zara.lead_id)
    assert zara.sequence_status == SequenceStatus.BOUNCED and db.is_suppressed("ahmed@zarafabrics.pk")


def test_bounce_previously_misread_as_reply_is_corrected(db, campaign, osettings, templates, tmp_path):
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    send_due(db, campaign, osettings, templates, FakeSender(), ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    zara = next(l for l in db.list_leads("test-retail") if l.company_name == "Zara Fabrics")
    zara.sequence_status = SequenceStatus.REPLIED
    zara.reply_status = "replied: Delivery Status Notification (Failure)"
    db.update_lead(zara)
    bounce = InboundMessage(from_addr="mailer-daemon@googlemail.com", subject="Delivery Status Notification (Failure)",
                            body="ahmed@zarafabrics.pk could not be found", references=zara.thread_message_id)
    report = apply_inbound(db, "test-retail", [bounce], ledger)
    assert report.bounced == 1
    assert db.get_lead(zara.lead_id).sequence_status == SequenceStatus.BOUNCED


# --- human approval ----------------------------------------------------------------------

def test_approval_gate_blocks_until_draft_approved(db, campaign, osettings, templates, tmp_path):
    from gtm_engine.outreach.sequencer import prepare_drafts
    osettings.require_approval = True
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    sender = FakeSender()

    # Nothing goes out without an approved draft
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 0 and r.skipped == 2 and sender.sent == []

    queue = prepare_drafts(db, campaign, osettings, templates, now=MON_10AM_PKT)
    assert [(q["step"], q["draft"]["status"]) for q in queue] == [("email_1", "pending"), ("email_1", "pending")]
    zara = next(q for q in queue if q["lead"].company_name == "Zara Fabrics")

    # Human edits the body and approves; the edited text is what gets sent
    db.upsert_draft(zara["lead"].lead_id, "email_1", "Custom subject", "Hi Ahmed, edited by a human.", status="approved", edited=True)
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 1 and r.skipped == 1
    assert sender.sent[0].subject == "Custom subject" and "edited by a human" in sender.sent[0].body
    assert db.get_draft(zara["lead"].lead_id, "email_1")["status"] == "sent"

    # Follow-up needs its own approval: 3 days later a new pending draft appears, nothing is sent
    day3 = MON_10AM_PKT + timedelta(days=3)
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=day3, sleep=lambda s: None)
    assert r.sent == 0
    queue = prepare_drafts(db, campaign, osettings, templates, now=day3)
    assert any(q["step"] == "followup_1" and q["lead"].company_name == "Zara Fabrics" for q in queue)


def test_rejected_draft_is_never_sent(db, campaign, osettings, templates, tmp_path):
    from gtm_engine.outreach.sequencer import prepare_drafts
    osettings.require_approval = True
    ledger = Ledger(tmp_path / "ledger.json")
    enqueue(db, "test-retail", osettings, ledger, now=MON_10AM_PKT)
    for q in prepare_drafts(db, campaign, osettings, templates, now=MON_10AM_PKT):
        db.set_draft_status(q["lead"].lead_id, q["step"], "rejected")
    sender = FakeSender()
    r = send_due(db, campaign, osettings, templates, sender, ledger, now=MON_10AM_PKT, sleep=lambda s: None)
    assert r.sent == 0 and sender.sent == []
