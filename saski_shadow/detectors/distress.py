"""Baseline distress indicator detection.

This module provides a conservative public baseline distress indicator list.
It is not clinical crisis detection and must not be used as the sole safety
layer for any regulated deployment.

The baseline list below uses synthetic tokens only. Real indicator content
is supplied by integrators via ``extra_indicators`` or by the licensed
SASKI engine. The list contains nothing proprietary and encodes no
algorithmic thresholds or weights.

Outcome behavior (baseline): a distress phrase match alone never blocks. When
``escalation_detected`` is True and no policy rule or PII block applies, the
analyzer assigns ``PublicOutcome.WARN``. In shadow mode the warning is
observed with ``enforcement_suppressed`` True rather than acted upon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Phrase list intentionally uses synthetic tokens. Real indicator content is
# supplied by integrators via the extra_indicators parameter or by the
# licensed SASKI engine.
_BASELINE_INDICATORS = (
    "synthetic-distress-token-alpha",
    "synthetic-distress-token-beta",
    "synthetic-distress-token-gamma",
)


@dataclass(frozen=True)
class DistressResult:
    escalation_detected: bool = False
    matched_indicators: list[str] = field(default_factory=list)


def detect_distress(
    text: str,
    extra_indicators: list[str] | None = None,
) -> DistressResult:
    """Return whether any baseline distress indicator phrase is present."""
    if not isinstance(text, str) or not text:
        return DistressResult(escalation_detected=False, matched_indicators=[])

    haystack = text.lower()
    indicators = list(_BASELINE_INDICATORS)
    if extra_indicators:
        indicators.extend(str(phrase).lower() for phrase in extra_indicators)

    # Matching strategy (changed): the previous implementation used unbounded
    # substring matching (``phrase in haystack``), which fired an indicator like
    # "sad" inside larger words such as "Saddleback". It now uses word-boundary
    # matching so an indicator only matches whole-word occurrences: "sad" hits
    # "I feel sad today" but not "Saddleback mountain". No threshold, weighting,
    # or indicator-list change is introduced.
    matched = [
        phrase
        for phrase in indicators
        if re.search(r"\b" + re.escape(phrase) + r"\b", haystack, re.IGNORECASE)
    ]
    # De-duplicate while preserving first-seen order.
    seen: set[str] = set()
    unique = [p for p in matched if not (p in seen or seen.add(p))]

    return DistressResult(
        escalation_detected=bool(unique),
        matched_indicators=unique,
    )
