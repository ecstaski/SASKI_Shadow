"""Baseline distress indicator detection.

This module provides a conservative public baseline distress indicator list.
It is not clinical crisis detection and must not be used as the sole safety
layer for any regulated deployment.

The indicator phrases below are generic, plain-language help-seeking
expressions of the kind described in publicly available mental health first
aid guidance and academic literature. The list contains nothing proprietary
and encodes no thresholds, weights, or semantic anchors.

Outcome behavior (baseline): a distress phrase match alone never blocks. When
``escalation_detected`` is True and no policy rule or PII block applies, the
analyzer assigns ``PublicOutcome.WARN``. In shadow mode the warning is
observed with ``enforcement_suppressed`` True rather than acted upon.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Generic, plain-language help-seeking indicators. Integrators may extend this
# list with their own phrases via the ``extra_indicators`` argument.
_BASELINE_INDICATORS = (
    "i want to hurt myself",
    "i want to harm myself",
    "i want to end it",
    "i can't go on",
    "i feel hopeless",
    "i have no reason to live",
    "i don't want to be here anymore",
    "thoughts of suicide",
    "self harm",
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

    matched = [phrase for phrase in indicators if phrase in haystack]
    # De-duplicate while preserving first-seen order.
    seen: set[str] = set()
    unique = [p for p in matched if not (p in seen or seen.add(p))]

    return DistressResult(
        escalation_detected=bool(unique),
        matched_indicators=unique,
    )
