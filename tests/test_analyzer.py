"""Tests for the baseline analyzer pipeline using synthetic stub data only."""

from unittest.mock import patch

from saski_shadow.analyzer import analyze_turn
from saski_shadow.analyzer.executor import MODE_TO_DOMAINS
from saski_shadow.laws import match_laws

TOKEN_EMAIL_A = "token-email-aaa-001"
TOKEN_SSN_A = "token-ssn-aaa-001"

_STAGES = {
    "normalize_input",
    "detect_pii",
    "detect_distress",
    "detect_adversarial",
    "detect_clinical_intent",
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


def test_pipeline_records_all_stage_timings():
    result = analyze_turn("the purple widget hums quietly")
    assert set(result.metadata["engine_summary"]["phase_timings"]) == _STAGES


def test_synthetic_token_message_stays_clean_tier():
    result = analyze_turn(f"reach me at {TOKEN_EMAIL_A}")
    summary = result.metadata["engine_summary"]
    assert result.pii_detected is False
    assert result.should_block is False
    assert summary["governance_tier"] == "tier_clean"


def test_distress_indicator_warns_and_does_not_block():
    result = analyze_turn("honestly I want to die")
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


def test_mode_child_is_recorded_on_result_and_summary():
    result = analyze_turn("the purple widget hums quietly", mode="child")
    assert result.mode == "child"
    assert result.metadata["engine_summary"]["mode"] == "child"


def test_mode_none_is_recorded_as_none():
    result = analyze_turn("the purple widget hums quietly", mode=None)
    assert result.mode is None
    assert result.metadata["engine_summary"]["mode"] is None


def test_unrecognized_mode_falls_back_to_none():
    result = analyze_turn("the purple widget hums quietly", mode="invalid_mode")
    assert result.mode is None
    assert result.metadata["engine_summary"]["mode"] is None


def test_message_for_llm_carries_redacted_egress_payload():
    result = analyze_turn("my ssn is 123-45-6789")
    assert result.message_for_llm is not None
    assert "123-45-6789" not in result.message_for_llm
    assert "[REDACTED_SSN]" in result.message_for_llm


def test_message_for_llm_passthrough_for_clean_text():
    result = analyze_turn("the purple widget hums quietly")
    assert result.message_for_llm == "the purple widget hums quietly"


def test_domains_list_is_carried_through_and_domain_mirrors_first():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"domains": ["consumer_chatbot", "csam"]},
    )
    assert result.domains == ["consumer_chatbot", "csam"]
    assert result.domain == "consumer_chatbot"
    summary = result.metadata["engine_summary"]
    assert summary["domains"] == ["consumer_chatbot", "csam"]
    assert summary["domain"] == "consumer_chatbot"


def test_single_domain_string_is_normalized_to_one_element_list():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"domain": "healthcare"},
    )
    assert result.domains == ["healthcare"]
    assert result.domain == "healthcare"
    summary = result.metadata["engine_summary"]
    assert summary["domains"] == ["healthcare"]
    assert summary["domain"] == "healthcare"


def test_no_domain_yields_empty_list_and_none_without_raising():
    result = analyze_turn("the purple widget hums quietly", session_context={})
    assert result.domains == []
    assert result.domain is None
    summary = result.metadata["engine_summary"]
    assert summary["domains"] == []
    assert summary["domain"] is None
    assert summary["domains_source"] == "none"


def test_domains_precedence_over_domain_when_both_present():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"domain": "healthcare", "domains": ["consumer_chatbot", "csam"]},
    )
    assert result.domains == ["consumer_chatbot", "csam"]
    assert result.domain == "consumer_chatbot"
    assert result.metadata["engine_summary"]["domains_source"] == "explicit"


def test_mode_derives_domains_when_explicit_domain_absent():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"user_jurisdiction": "US-NY"},
        mode="mental_health_support",
    )
    assert result.domains == ["mental_health", "consumer_chatbot"]
    assert result.metadata["engine_summary"]["domains_source"] == "mode_derived"
    matched = match_laws("US-NY", result.domains)
    ids = {law["law_id"] for law in matched}
    assert "US-NY-AI-COMPANION" in ids


def test_explicit_domain_overrides_mode_derived_domains():
    result = analyze_turn(
        "the purple widget hums quietly",
        session_context={"domain": "employment", "user_jurisdiction": "US-NY-NYC"},
        mode="child",
    )
    assert result.domains == ["employment"]
    assert result.metadata["engine_summary"]["domains_source"] == "explicit"


def test_unmapped_valid_mode_falls_back_to_consumer_chatbot():
    with patch.dict(MODE_TO_DOMAINS, {}, clear=True):
        result = analyze_turn(
            "the purple widget hums quietly",
            mode="patient",
        )
    assert result.domains == ["consumer_chatbot"]
    assert result.metadata["engine_summary"]["domains_source"] == "mode_derived"
