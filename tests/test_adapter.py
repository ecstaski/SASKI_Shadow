"""Tests for the result->persisted-turn adapter and the full pipeline.

These exercise the real path with no fabricated engine_summary:
    analyze_turn() -> result_to_jsonl_turn() -> aggregate_shadow_report()
"""

import json

from saski_shadow import (
    aggregate_shadow_report,
    load_turns_jsonl,
    result_to_jsonl_turn,
)
from saski_shadow.analyzer import analyze_turn

# Realistic synthetic PHI: a separator-delimited SSN and an email both match the
# baseline detector, so the PII section is genuinely driven by detection.
PHI_MESSAGE = "my ssn is 123-45-6789 and email me at patient@example.com"

_REQUIRED_TURN_KEYS = {
    "turn_index",
    "session_id",
    "timestamp_utc",
    "input_hash",
    "output_hash",
    "latency_ms",
    "mode_tag",
    "envelope",
    "engine_summary",
    "transport_audit_record",
    "compliance_decisions",
    "output_review",
}


def test_adapter_produces_required_aggregator_fields():
    result = analyze_turn(
        PHI_MESSAGE,
        session_context={"user_jurisdiction": "US-CA", "domain": "healthcare"},
        mode="patient",
    )
    turn = result_to_jsonl_turn(result, session_id="sess_a", turn_index=0)

    assert _REQUIRED_TURN_KEYS.issubset(turn)

    # The full engine_summary (not the slim evidence one) must come through.
    summary = turn["engine_summary"]
    for key in (
        "governance_tier",
        "pii_detected",
        "pii_types",
        "escalation_detected",
        "would_block",
        "outcome",
        "user_jurisdiction",
        "domain",
        "mode",
    ):
        assert key in summary
    assert summary["user_jurisdiction"] == "US-CA"
    assert summary["domain"] == "healthcare"
    assert summary["mode"] == "patient"
    # Hashes were hoisted from the envelope to the top level.
    assert turn["input_hash"]
    assert turn["mode_tag"] == "shadow_mode"


def test_adapter_provider_id_passthrough():
    result = analyze_turn("the purple widget hums quietly")
    turn = result_to_jsonl_turn(
        result, session_id="sess_b", turn_index=2, provider_id="anthropic"
    )
    assert turn["provider_id"] == "anthropic"
    assert turn["turn_index"] == 2


def test_full_pipeline_produces_non_empty_report(tmp_path):
    # analyze two real turns, adapt them, persist to JSONL, then aggregate.
    results = [
        analyze_turn(
            PHI_MESSAGE,
            session_context={"user_jurisdiction": "US-CA", "domain": "healthcare"},
            mode="patient",
        ),
        analyze_turn(
            "the purple widget hums quietly",
            session_context={"user_jurisdiction": "US-CA", "domain": "healthcare"},
            mode="patient",
        ),
    ]
    turns = [
        result_to_jsonl_turn(r, session_id="sess_e2e", turn_index=i)
        for i, r in enumerate(results)
    ]

    path = tmp_path / "turns.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        for turn in turns:
            handle.write(json.dumps(turn) + "\n")

    loaded = load_turns_jsonl(str(path))
    assert len(loaded) == 2

    report = aggregate_shadow_report(loaded)

    # Eight sections, correct structure.
    assert report["schema_version"] == "shadow_report_v1"
    assert len(report["sections"]) == 8

    # Section 1 reflects real detection on the first turn.
    pii = report["sections"]["pii_phi_detection_summary"]
    assert pii["totals"]["turns_processed"] == 2
    assert pii["totals"]["turns_with_pii"] == 1
    assert pii["by_pii_type"]["ssn"] == 1
    assert pii["by_pii_type"]["email"] == 1

    # Section 2 surfaces CA + federal healthcare laws from the metadata.
    compliance = report["sections"]["compliance_exposure_examples"]
    assert compliance["law_match_summary"]["turns_with_law_match"] == 2
    unique = set(compliance["law_match_summary"]["unique_law_ids"])
    assert {"US-CA-AB3030-HEALTH", "US-HIPAA"}.issubset(unique)
