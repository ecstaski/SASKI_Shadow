"""Axis 3 - full pipeline golden tests.

Each test runs the real path end-to-end with no fabricated engine_summary:
    analyze_turn() -> result_to_jsonl_turn() -> write JSONL -> aggregate_shadow_report()
and asserts on the produced report. Covers one golden test per domain plus
cross-domain isolation (gap 5) and federal-only (gap 4).
"""

from __future__ import annotations

import json

from saski_shadow import aggregate_shadow_report, load_turns_jsonl, result_to_jsonl_turn
from saski_shadow.analyzer import analyze_turn

_PHI_TEXT = "My SSN is 123-45-6789 and email me at patient@example.com about results."

_METHODOLOGY_KEYS = {
    "detector_profile",
    "law_set_version",
    "law_set_sync_date",
    "total_laws_evaluated",
    "total_jurisdictions",
    "schema_version",
    "report_period",
}


def _run(tmp_path, message, session_context, *, mode=None):
    result = analyze_turn(message, session_context=session_context, mode=mode)
    turn = result_to_jsonl_turn(result, session_id="sess_axis3", turn_index=0)
    path = tmp_path / "turns.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(turn) + "\n")
    return aggregate_shadow_report(load_turns_jsonl(str(path)))


def _section(report, name):
    return report["sections"][name]


def _law_ids(report):
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    return {law["law_id"] for law in matched}


def _assert_common_credibility(report):
    compliance = _section(report, "compliance_exposure_examples")
    assert "detection_limitations" in compliance
    assert set(compliance["matched_laws_by_status"]) == {"in_force", "future_effective"}
    assert _section(report, "recommended_path")["section"] == "recommended_path"
    assert set(report["methodology"]) == _METHODOLOGY_KEYS


def test_healthcare_pipeline_golden(tmp_path):
    report = _run(
        tmp_path,
        _PHI_TEXT,
        {"user_jurisdiction": "US-CA", "domain": "healthcare"},
        mode="patient",
    )
    # Section 1: PII reflects the SSN/email actually in the input.
    pii = _section(report, "pii_phi_detection_summary")
    assert pii["totals"]["turns_with_pii"] == 1
    assert pii["by_pii_type"]["ssn"] == 1
    # Section 2: expected healthcare laws present.
    ids = _law_ids(report)
    assert {"US-CA-AB3030-HEALTH", "US-HIPAA"}.issubset(ids)
    _assert_common_credibility(report)
    # Negative: no wrong-domain laws, no US-NY-only laws.
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    assert all(law["domain"] == "healthcare" for law in matched)
    assert not any(law["law_id"].startswith("US-NY") for law in matched)


def test_ca_healthcare_cross_domain_isolation(tmp_path):
    # Gap 5: a US-CA / healthcare pipeline must not surface employment or csam.
    report = _run(tmp_path, _PHI_TEXT, {"user_jurisdiction": "US-CA", "domain": "healthcare"})
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    domains = {law["domain"] for law in matched}
    assert "employment" not in domains
    assert "csam" not in domains


def test_federal_healthcare_pipeline_only_federal_laws(tmp_path):
    # Gap 4: US / healthcare surfaces HIPAA and no state laws.
    report = _run(
        tmp_path,
        "How is my health data protected?",
        {"user_jurisdiction": "US", "domain": "healthcare"},
    )
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    ids = {law["law_id"] for law in matched}
    assert "US-HIPAA" in ids
    assert all(law["jurisdiction"] == "US" for law in matched)
    _assert_common_credibility(report)


def test_consumer_chatbot_pipeline_golden(tmp_path):
    report = _run(
        tmp_path,
        "How do I stay safe chatting online?",
        {"user_jurisdiction": "US-CA", "domain": "consumer_chatbot"},
        mode="child",
    )
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    assert matched
    assert all(law["domain"] == "consumer_chatbot" for law in matched)
    _assert_common_credibility(report)


def test_employment_pipeline_golden(tmp_path):
    report = _run(
        tmp_path,
        "Please rank these job applicants by resume strength.",
        {"user_jurisdiction": "US-NY-NYC", "domain": "employment"},
        mode="hr_recruiting",
    )
    ids = _law_ids(report)
    assert "US-NYC-AEDT" in ids
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    assert all(law["domain"] == "employment" for law in matched)
    _assert_common_credibility(report)


def test_csam_pipeline_golden(tmp_path):
    report = _run(
        tmp_path,
        "A stranger online keeps pressuring me and it makes me uncomfortable.",
        {"user_jurisdiction": "US", "domain": "csam"},
        mode="child",
    )
    matched = _section(report, "compliance_exposure_examples")["matched_laws"]
    assert matched
    assert all(law["domain"] == "csam" for law in matched)
    _assert_common_credibility(report)


def test_mental_health_pipeline_escalation_matches_indicators(tmp_path):
    report = _run(
        tmp_path,
        "Lately I feel hopeless and unmotivated.",
        {
            "user_jurisdiction": "US-NY",
            "domain": "mental_health",
            "extra_distress_indicators": ["feel hopeless"],
        },
        mode="mental_health_support",
    )
    escalation = _section(report, "escalation_signal_count")
    assert escalation["totals"]["escalation_turns"] == 1
    _assert_common_credibility(report)
