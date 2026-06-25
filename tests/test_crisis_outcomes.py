"""Crisis-outcome structural / schema tests (2A).

The baseline package never produces a crisis outcome. ``is_crisis`` is hardwired
to ``False`` and ``_decide_outcome`` can only return allow / warn / block /
human_review. Real crisis detection (crisis_referral, physical_emergency_referral,
immutable 988 templates, physical-emergency routing) is a licensed-SASKI-SDK
capability and lives in the private engine.

These tests document that boundary *structurally* — they never assert the
baseline CAN produce a crisis signal, which per AGENTS.md (SDK-alignment rules)
would be a false failure for a signal the baseline cannot emit. Instead they
prove:

  1. No matter how distress-laden the input, the baseline never emits a crisis
     outcome or sets ``is_crisis=True``.
  2. The public outcome vocabulary and the report JSON schema still RESERVE the
     two crisis outcomes, and the report's ``by_outcome`` map carries them at
     zero for a baseline session — so a licensed-SDK turn store that DOES emit
     them validates and aggregates without any schema change.
  3. The governance-tier mapping already routes a crisis outcome to
     ``tier_escalation``, so the wiring is correct the day the licensed engine
     emits one.
"""

from __future__ import annotations

import json
import pathlib

import saski_shadow
from saski_shadow import aggregate_shadow_report, load_turns_jsonl, result_to_jsonl_turn
from saski_shadow.analyzer import analyze_turn
from saski_shadow.analyzer.executor import _governance_tier
from saski_shadow.enums import PublicOutcome

# Distress-laden inputs with integrator-supplied indicators. The baseline can at
# most surface these as a 'warn'; it must never reclassify them as crisis.
_DISTRESS_INPUTS = [
    (
        "Lately I feel hopeless and I cannot go on.",
        {"extra_distress_indicators": ["feel hopeless", "cannot go on"]},
    ),
    (
        "I want to hurt myself and I do not know what to do.",
        {"extra_distress_indicators": ["hurt myself"]},
    ),
    (
        "There is an emergency and someone is in danger right now.",
        {"extra_distress_indicators": ["emergency", "in danger"]},
    ),
]

_CRISIS_OUTCOMES = {"crisis_referral", "physical_emergency_referral"}
_BASELINE_OUTCOMES = {"allow", "warn", "block", "human_review"}


def test_baseline_never_produces_crisis_outcome_or_flag():
    for message, ctx in _DISTRESS_INPUTS:
        result = analyze_turn(message, session_context=ctx, mode="mental_health_support")
        assert result.is_crisis is False, f"is_crisis should stay False for {message!r}"
        assert result.action in _BASELINE_OUTCOMES
        assert result.action not in _CRISIS_OUTCOMES


def test_public_outcome_vocabulary_reserves_crisis_outcomes():
    values = {o.value for o in PublicOutcome}
    assert _CRISIS_OUTCOMES.issubset(values)


def test_report_by_outcome_reserves_crisis_keys_at_zero(tmp_path):
    # A distress turn: escalation surfaces as 'warn'; both crisis keys stay 0 but
    # are always present in the map.
    result = analyze_turn(
        "Lately I feel hopeless.",
        session_context={"extra_distress_indicators": ["feel hopeless"]},
        mode="mental_health_support",
    )
    turn = result_to_jsonl_turn(result, session_id="sess_crisis", turn_index=0)
    path = tmp_path / "turns.jsonl"
    path.write_text(json.dumps(turn) + "\n", encoding="utf-8")
    report = aggregate_shadow_report(load_turns_jsonl(str(path)))

    by_outcome = report["sections"]["escalation_signal_count"]["by_outcome"]
    assert by_outcome["crisis_referral"] == 0
    assert by_outcome["physical_emergency_referral"] == 0
    assert by_outcome["warn"] == 1


def test_report_schema_enumerates_crisis_outcomes():
    # The report schema must keep the crisis values in its public_outcome enum so
    # a licensed-SDK turn store validates without a schema change.
    schema_path = (
        pathlib.Path(saski_shadow.__file__).parent / "schemas" / "shadow_report_v1.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    enum = schema["$defs"]["public_outcome"]["enum"]
    assert "crisis_referral" in enum
    assert "physical_emergency_referral" in enum

    by_outcome_props = schema["$defs"]["escalation_signal_count"]["properties"][
        "by_outcome"
    ]["properties"]
    assert "crisis_referral" in by_outcome_props
    assert "physical_emergency_referral" in by_outcome_props


def test_governance_tier_maps_crisis_outcome_to_escalation():
    # Documents that the tier wiring already routes a crisis outcome to
    # tier_escalation, even though the baseline never emits one.
    for outcome in (
        PublicOutcome.CRISIS_REFERRAL,
        PublicOutcome.PHYSICAL_EMERGENCY_REFERRAL,
    ):
        tier = _governance_tier(
            would_block=False,
            escalation_detected=False,
            outcome=outcome,
            pii_detected=False,
        )
        assert tier == "tier_escalation", f"{outcome.value} should map to tier_escalation"
