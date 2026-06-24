"""Tests for the baseline detectors using synthetic stub data only."""

from saski_shadow.detectors import (
    DETECTORS,
    detect_distress,
    detect_pii,
    evaluate_policy,
    review_output,
)

TOKEN_EMAIL_A = "token-email-aaa-001"
TOKEN_SSN_A = "token-ssn-aaa-001"
TOKEN_PHONE_A = "token-phone-aaa-001"
TOKEN_IP_A = "token-ip-aaa-001"


def test_pii_detector_ignores_synthetic_tokens():
    result = detect_pii(
        f"contact {TOKEN_EMAIL_A} ssn {TOKEN_SSN_A} ip {TOKEN_IP_A}"
    )
    assert result.pii_types == []
    assert result.redaction_applied is False
    assert TOKEN_EMAIL_A in result.redacted_text


def test_pii_detector_returns_clean_for_plain_text():
    result = detect_pii("the purple widget hums quietly")
    assert result.pii_types == []
    assert result.redaction_applied is False


def test_distress_detector_matches_synthetic_indicator():
    result = detect_distress("message synthetic-distress-token-alpha payload")
    assert result.escalation_detected is True
    assert "synthetic-distress-token-alpha" in result.matched_indicators


def test_distress_detector_ignores_unrelated_synthetic_text():
    result = detect_distress("the purple widget hums quietly")
    assert result.escalation_detected is False
    assert result.matched_indicators == []


def test_policy_evaluator_returns_matched_integrator_rules():
    policy = {
        "policy_id": "policy_test",
        "rules": [
            {
                "id": "rule_one",
                "when": {"pii_types_any": ["email"]},
                "action": "block",
                "reason_code": "INTEGRATOR_CODE_ONE",
            }
        ],
    }
    signals = {"text": "x", "pii_detected": True, "pii_types": ["email"], "escalation_detected": False}
    decisions = evaluate_policy(signals, policy)
    assert len(decisions) == 1
    assert decisions[0]["action"] == "block"
    assert decisions[0]["reason_code"] == "INTEGRATOR_CODE_ONE"


def test_policy_evaluator_returns_empty_without_policy():
    assert evaluate_policy({"text": "x"}, None) == []


def test_output_review_flags_human_claim():
    result = review_output("a human will contact you")
    assert result.human_escalation_claimed is True
    assert result.pii_leaked_types == []


def test_output_review_flags_integrator_boundary_phrase():
    result = review_output(
        "this reply contains a synthetic boundary marker",
        policy={"output_boundary_phrases": ["synthetic boundary marker"]},
    )
    assert "synthetic boundary marker" in result.policy_boundary_hits


def test_registry_exposes_four_detectors():
    assert set(DETECTORS) == {"pii", "distress", "policy", "output_review"}


def test_distress_extra_indicator_does_not_match_substring_of_larger_word():
    # Word-boundary precision: a 'sad' indicator must NOT match 'Saddleback'.
    result = detect_distress("Saddleback mountain trail", extra_indicators=["sad"])
    assert result.escalation_detected is False


def test_distress_extra_indicator_matches_whole_word():
    # The same indicator still fires on a genuine whole-word occurrence.
    result = detect_distress("honestly I feel sad today", extra_indicators=["sad"])
    assert result.escalation_detected is True
    assert "sad" in result.matched_indicators


def test_distress_multi_word_indicator_respects_word_boundaries():
    indicators = ["want to hurt"]
    hit = detect_distress("I want to hurt myself", extra_indicators=indicators)
    miss = detect_distress("I want to hurtle down the slope", extra_indicators=indicators)
    assert hit.escalation_detected is True
    assert miss.escalation_detected is False
