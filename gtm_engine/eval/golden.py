"""Golden-set harness: measure the classifier against hand-labelled real companies.

The reframe (PLAN.md) is quality over quantity, and the CEO's success metric is reviewer
accuracy >= 80%. That is only meaningful if we can measure it, so this scores the
BUYER/VENDOR/UNKNOWN gate – the decision the whole engine turns on – against a fixed set of
labelled examples. It is pure (no network, no DB), so it runs anywhere and every change can
be checked for a regression before it ships.

The seed set lives in tests/golden/golden_leads.jsonl. Add real, hand-labelled rows to it as
the campaigns run; the harness and the accuracy floor grow with it."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from gtm_engine.config.schema import CampaignConfig, DefaultRules, GeographyConfig
from gtm_engine.models import CompanyType
from gtm_engine.qualification.buyer_classifier import BuyerClassifier, TextBundle

GOLDEN_PATH = Path(__file__).resolve().parents[2] / "tests" / "golden" / "golden_leads.jsonl"


@dataclass
class GoldenRecord:
    name: str
    expected_type: str                 # buyer | vendor | unknown
    title: str | None = None
    description: str | None = None
    about_text: str | None = None
    body_text: str = ""
    category: str | None = None
    site_reachable: bool = True
    note: str = ""

    def bundle(self) -> TextBundle:
        return TextBundle(
            name=self.name, title=self.title, description=self.description,
            about_text=self.about_text, body_text=self.body_text or self.about_text or self.name,
            category=self.category, site_reachable=self.site_reachable,
        )


def load_golden(path: Path | None = None) -> list[GoldenRecord]:
    lines = (path or GOLDEN_PATH).read_text(encoding="utf-8").splitlines()
    out: list[GoldenRecord] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        out.append(GoldenRecord(**json.loads(line)))
    return out


def default_campaign() -> CampaignConfig:
    """The campaign the seed rows are labelled against: a retail / consumer-goods buyer hunt,
    the case where telling a real retailer apart from a web/IT agency matters most."""
    return CampaignConfig(
        campaign_id="golden-retail", name="Golden retail", offer="inventory and order software",
        target_industries=["retail", "clothing", "fashion", "electronics", "furniture", "garment", "supermarket"],
        geography=GeographyConfig(countries=["Pakistan"]),
        buyer_keywords=["retailer", "store", "brand", "outlet", "shop", "boutique", "showroom", "supermarket", "mart"],
        osm_categories=["shop=clothes", "shop=furniture", "shop=electronics", "shop=*"],
    )


@dataclass
class Report:
    total: int = 0
    correct: int = 0
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)
    misses: list[tuple[GoldenRecord, str]] = field(default_factory=list)  # (record, predicted)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    def per_label(self) -> dict[str, tuple[int, int]]:
        """label -> (correct, total) so a class the seed is thin on is visible."""
        out: dict[str, list[int]] = {}
        for (expected, predicted), n in self.confusion.items():
            slot = out.setdefault(expected, [0, 0])
            slot[1] += n
            if expected == predicted:
                slot[0] += n
        return {k: (v[0], v[1]) for k, v in out.items()}


def evaluate(records: list[GoldenRecord], campaign: CampaignConfig | None = None,
             defaults: DefaultRules | None = None) -> Report:
    from gtm_engine.config.loader import load_defaults

    campaign = campaign or default_campaign()
    defaults = defaults or load_defaults()
    classifier = BuyerClassifier(campaign, defaults)
    report = Report()
    for rec in records:
        predicted = classifier.classify(rec.bundle()).company_type.value.lower()
        expected = rec.expected_type.lower()
        report.total += 1
        key = (expected, predicted)
        report.confusion[key] = report.confusion.get(key, 0) + 1
        if predicted == expected:
            report.correct += 1
        else:
            report.misses.append((rec, predicted))
    return report


def format_report(report: Report) -> str:
    lines = [f"Golden-set accuracy: {report.correct}/{report.total} = {report.accuracy:.0%}", ""]
    for label, (correct, total) in sorted(report.per_label().items()):
        lines.append(f"  {label:<8} {correct}/{total}")
    if report.misses:
        lines += ["", "Misclassified:"]
        for rec, predicted in report.misses:
            lines.append(f"  {rec.name!r}: expected {rec.expected_type}, got {predicted}"
                         + (f"  ({rec.note})" if rec.note else ""))
    return "\n".join(lines)


# CompanyType kept imported for callers that want the enum rather than strings.
_ = CompanyType
