"""Integrator policy evaluation.

Evaluates a single turn against rules supplied entirely by the integrator.
There is no built-in statute logic, jurisdiction database, or default rule
set in this module.

Policy input is a plain Python dict only. To keep the package at zero runtime
dependencies, this module never reads YAML. If you keep policies in YAML,
load them yourself with any YAML library and pass the resulting dict in.

Returns a list of compliance decisions whose ``reason_code`` and
``obligation_label`` values are integrator-defined and passed through
verbatim.
"""

from __future__ import annotations

from typing import Any


def _condition_matches(when: dict[str, Any], signals: dict[str, Any]) -> bool:
    if not isinstance(when, dict):
        return False

    if "pii_detected" in when:
        if bool(signals.get("pii_detected", False)) != bool(when["pii_detected"]):
            return False

    if "escalation_detected" in when:
        if bool(signals.get("escalation_detected", False)) != bool(when["escalation_detected"]):
            return False

    if "pii_types_any" in when:
        wanted = {str(t).lower() for t in when.get("pii_types_any") or []}
        present = {str(t).lower() for t in signals.get("pii_types") or []}
        if not (wanted & present):
            return False

    if "contains_any" in when:
        haystack = str(signals.get("text", "")).lower()
        phrases = [str(p).lower() for p in when.get("contains_any") or []]
        if not any(phrase in haystack for phrase in phrases):
            return False

    return True


def evaluate_policy(
    signals: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate integrator rules against turn signals; return matched decisions."""
    if not policy or not isinstance(policy, dict):
        return []

    rules = policy.get("rules")
    if not isinstance(rules, list):
        return []

    decisions: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        when = rule.get("when", {})
        if not _condition_matches(when, signals):
            continue
        decisions.append(
            {
                "rule_id": rule.get("id"),
                "action": rule.get("action"),
                "reason_code": rule.get("reason_code"),
                "obligation_label": rule.get("obligation_label"),
            }
        )

    return decisions
