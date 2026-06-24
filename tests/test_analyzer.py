"""Tests for the baseline analyzer pipeline using synthetic stub data only."""

from saski_shadow.analyzer import analyze_turn

TOKEN_EMAIL_A = "token-email-aaa-001"
TOKEN_SSN_A = "token-ssn-aaa-001"

_STAGES = {
    "normalize_input",
    "detect_pii",
    "detect_distress",
    "evaluate_policy",
    "review_output",
    "decide_outcome",
    "sanitize_egress",
    "build_evidence",
}


def test_clean_message_allows_and_stays_clean_tier():
    result = analyze_turn("the purple widget hums quietly")
    summary = result.metadata["engine_summary"]
    assert result.action == "allow"
    assert result.should_block is False
    assert result.is_crisis is False
    assert summary["governance_tier"] == "tier_clean"
    assert result.metadata["detector_profile"] == "baseline-v1"


def test_pipeline_records_all_eight_stage_timings():
    result = analyze_turn("the purple widget hums quietly")
    assert set(result.metadata["engine_summary"]["phase_timings"]) == _STAGES


def test_synthetic_token_message_stays_clean_tier():
    result = analyze_turn(f"reach me at {TOKEN_EMAIL_A}")
    summary = result.metadata["engine_summary"]
    assert result.pii_detected is False
    assert result.should_block is False
    assert summary["governance_tier"] == "tier_clean"


def test_distress_indicator_warns_and_does_not_block():
    result = analyze_turn("payload synthetic-distress-token-beta payload")
    summary = result.metadata["engine_summary"]
    assert summary["escalation_detected"] is True
    assert result.action == "warn"
    assert result.should_block is False
    assert summary["governance_tier"] == "tier_escalation"


def test_policy_block_rule_is_the_only_path_to_block():
    policy = {
        "policy_id": "policy_test",
        "rules": [
            {
                "id": "rule_one",
                "when": {"contains_any": [TOKEN_SSN_A]},
                "action": "block",
                "reason_code": "INTEGRATOR_CODE_ONE",
            }
        ],
    }
    result = analyze_turn(f"ref {TOKEN_SSN_A}", policy=policy)
    summary = result.metadata["engine_summary"]
    assert result.should_block is True
    assert result.action == "block"
    assert summary["governance_tier"] == "tier_escalation"


def test_output_review_runs_when_assistant_output_supplied():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"assistant_output": "a human will contact you shortly"},
    )
    review = result.metadata["output_review"]
    assert review["human_escalation_claimed"] is True
    assert result.envelope["output_hash"] is not None


def test_analyze_turn_passes_jurisdiction_and_domain_to_engine_summary():
    result = analyze_turn(
        "Hello, can you help me?",
        session_context={
            "user_jurisdiction": "US-CA",
            "domain": "healthcare",
        },
    )
    summary = result.metadata["engine_summary"]
    assert summary["user_jurisdiction"] == "US-CA"
    assert summary["domain"] == "healthcare"
