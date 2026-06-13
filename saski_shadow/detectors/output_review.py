"""Observable assistant-output review.

Reviews an assistant response using only observable, explainable signals:

1. PII present in the assistant output that was redacted from the user input.
2. Assistant claims that a human has been or will be involved.
3. Integrator-configured policy boundary phrases appearing in the output.

This module contains no adversarial, obfuscation, or drift logic and no
private detector categories. All signals are surface-observable text checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .pii import detect_pii

# Generic, plain-language claims that a human has been or will be involved.
# Integrators may extend via ``extra_escalation_claims``.
_HUMAN_ESCALATION_CLAIMS = (
    "connected you to a human",
    "connect you with a human",
    "transfer you to an agent",
    "transferring you to an agent",
    "a representative will",
    "a human will contact you",
    "speak to a human agent",
    "escalated to a person",
    "escalating to a human",
)


@dataclass(frozen=True)
class OutputReviewResult:
    pii_leaked_types: list[str] = field(default_factory=list)
    human_escalation_claimed: bool = False
    policy_boundary_hits: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)


def review_output(
    assistant_output: str,
    input_pii_types: list[str] | None = None,
    policy: dict[str, Any] | None = None,
    extra_escalation_claims: list[str] | None = None,
) -> OutputReviewResult:
    """Review assistant output for observable mismatch signals."""
    if not isinstance(assistant_output, str) or not assistant_output:
        return OutputReviewResult()

    haystack = assistant_output.lower()
    findings: list[dict[str, Any]] = []

    redacted_from_input = {str(t).lower() for t in input_pii_types or []}
    output_pii = set(detect_pii(assistant_output).pii_types)
    leaked = sorted(output_pii & redacted_from_input)
    if leaked:
        findings.append({"signal": "pii_in_output_was_redacted_from_input", "pii_types": leaked})

    claims = list(_HUMAN_ESCALATION_CLAIMS)
    if extra_escalation_claims:
        claims.extend(str(p).lower() for p in extra_escalation_claims)
    human_escalation_claimed = any(phrase in haystack for phrase in claims)
    if human_escalation_claimed:
        findings.append({"signal": "assistant_claimed_human_escalation"})

    boundary_phrases = []
    if isinstance(policy, dict):
        boundary_phrases = [str(p) for p in policy.get("output_boundary_phrases") or []]
    boundary_hits = [phrase for phrase in boundary_phrases if phrase.lower() in haystack]
    if boundary_hits:
        findings.append({"signal": "policy_boundary_phrase_present", "phrases": boundary_hits})

    return OutputReviewResult(
        pii_leaked_types=leaked,
        human_escalation_claimed=human_escalation_claimed,
        policy_boundary_hits=boundary_hits,
        findings=findings,
    )
