"""Baseline distress indicator detection.

This module provides a small baseline list of common crisis phrases. It is
**common phrase awareness only — not clinical crisis detection**, and must not
be used as the sole safety layer for any regulated deployment. The list catches
only literal, direct phrasings; it cannot detect indirect, contextual, or
semantic distress. Clinical-grade crisis detection that does not depend on a
phrase list is provided by the licensed SASKI engine.

The list contains nothing proprietary and encodes no algorithmic thresholds or
weights — it is a plain set of well-known public crisis phrases. Integrators may
extend it for a turn via ``extra_indicators``.

Outcome behavior (baseline): a distress phrase match alone never blocks. When
``escalation_detected`` is True and no policy rule or PII block applies, the
analyzer assigns ``PublicOutcome.WARN``. In shadow mode the warning is
observed with ``enforcement_suppressed`` True rather than acted upon.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Small baseline list of common, public, direct crisis phrases. Common phrase
# awareness only -- not clinical crisis detection. It matches literal phrasings
# only and will miss indirect/contextual/semantic distress. Integrators may add
# more phrases per turn via the extra_indicators parameter; the licensed SASKI
# engine provides clinical-grade detection without any phrase list.
_BASELINE_INDICATORS = (
    "kill myself",
    "killing myself",
    "end my life",
    "ending my life",
    "want to die",
    "wanna die",
    "hurt myself",
    "hurting myself",
    "harm myself",
    "harming myself",
    "suicide",
    "suicidal",
    "take my own life",
    "don't want to live",
    "no reason to live",
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
