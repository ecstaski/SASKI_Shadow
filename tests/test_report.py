"""Tests for shadow report aggregation over synthetic turn payloads."""

import json

from saski_shadow import PublicOutcome, aggregate_shadow_report, load_turns_jsonl
from saski_shadow.aggregate.report import (
    COMPLIANCE_DISCLAIMER,
    ESCALATION_DISCLAIMER,
    UPGRADE_MESSAGE,
)

HEX64_A = "a" * 64


def _turn(idx, session_id, *, outcome="allow", tier="tier_clean", pii=False,
          escalation=False, would_block=False, pii_types=None, latency=1.0):
    return {
        "turn_index": idx,
        "timestamp_utc": "2026-06-12T16:00:00+00:00",
        "session_id": session_id,
        "input_hash": HEX64_A,
        "mode_tag": "shadow_mode",
        "latency_ms": latency,
        "envelope": {},
        "transport_audit_record": {"pii_types": pii_types or [], "redaction_applied": pii},
        "engine_summary": {
            "outcome": outcome,
            "risk_band": "low",
            "pii_detected": pii,
            "pii_types": pii_types or [],
            "escalation_detected": escalation,
            "would_block": would_block,
            "governance_tier": tier,
            "phase_timings": {"stage_one": 0.5, "stage_two": 0.5},
        },
    }


def _sample_turns():
    return [
        _turn(0, "sess_test_001"),
        _turn(1, "sess_test_001", outcome="allow", tier="tier_warning", pii=True, pii_types=["email"]),
        _turn(2, "sess_test_002", outcome="warn", tier="tier_escalation", escalation=True),
        _turn(3, "sess_test_002", outcome="block", tier="tier_escalation", would_block=True),
    ]


def test_report_has_schema_version_and_eight_sections():
    report = aggregate_shadow_report(_sample_turns())
    assert report["schema_version"] == "shadow_report_v1"
    assert len(report["sections"]) == 8


def test_absent_governance_tier_defaults_to_tier_clean():
    turn = {"turn_index": 0, "session_id": "sess_test_001", "engine_summary": {"outcome": "allow"}}
    report = aggregate_shadow_report([turn])
    measured = report["sections"]["token_savings_calculation"]["measured_from_shadow"]
    assert measured["tier_clean_turns"] == 1


def test_by_outcome_uses_public_outcome_vocabulary_only():
    report = aggregate_shadow_report(_sample_turns())
    by_outcome = report["sections"]["escalation_signal_count"]["by_outcome"]
    assert set(by_outcome) == {o.value for o in PublicOutcome}


def test_unsafe_flow_categories_are_the_six_neutral_values():
    report = aggregate_shadow_report(_sample_turns())
    categories = report["sections"]["unsafe_flow_documentation"]["categories"]
    assert set(categories) == {
        "enforcement_would_block",
        "policy_boundary_failure",
        "content_sanitization_gap",
        "integrator_override",
        "manual_review_required",
        "other",
    }


def test_required_messaging_present_in_sections_two_three_five():
    report = aggregate_shadow_report(_sample_turns())
    sections = report["sections"]
    assert sections["compliance_exposure_examples"]["disclaimer"] == COMPLIANCE_DISCLAIMER
    assert sections["compliance_exposure_examples"]["upgrade_path"] == UPGRADE_MESSAGE
    assert sections["token_savings_calculation"]["upgrade_path"] == UPGRADE_MESSAGE
    assert sections["escalation_signal_count"]["disclaimer"] == ESCALATION_DISCLAIMER
    assert sections["escalation_signal_count"]["upgrade_path"] == UPGRADE_MESSAGE


def test_counts_reflect_pii_and_escalation_turns():
    report = aggregate_shadow_report(_sample_turns())
    assert report["sections"]["pii_phi_detection_summary"]["totals"]["turns_with_pii"] == 1
    assert report["sections"]["escalation_signal_count"]["totals"]["escalation_turns"] == 1


def test_load_turns_jsonl_round_trip(tmp_path):
    path = tmp_path / "turns.jsonl"
    turns = _sample_turns()
    with open(path, "w", encoding="utf-8") as handle:
        for turn in turns:
            handle.write(json.dumps(turn) + "\n")
        handle.write("\n")  # blank line should be skipped
    loaded = load_turns_jsonl(str(path))
    assert len(loaded) == len(turns)
