"""Strict text-relevance matching.

The P2 rule: a hiring or intent signal only counts if it is relevant to *what this campaign
sells*. "A company is hiring" is not a buying signal on its own – a retailer hiring a
cashier tells us nothing about whether it wants inventory software. So a signal must contain
at least one of the campaign's relevance keywords, matched on whole words (no substring
false positives like 'art' inside 'cart')."""

from __future__ import annotations

import re


def relevant_terms(text: str, keywords: list[str]) -> list[str]:
    """Every keyword that appears in `text` on a word boundary, case-insensitive. A multi-word
    keyword matches as a phrase. Empty when nothing matches."""
    if not text or not keywords:
        return []
    low = text.lower()
    hits: list[str] = []
    for kw in keywords:
        kw = (kw or "").strip().lower()
        if not kw:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
        if re.search(pattern, low):
            hits.append(kw)
    return hits


def is_relevant(text: str, keywords: list[str]) -> bool:
    return bool(relevant_terms(text, keywords))
