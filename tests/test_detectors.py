"""Tests for the baseline detectors using synthetic stub data only."""

from saski_shadow.detectors import (
    DETECTORS,
    detect_distress,
    detect_pii,
    evaluate_policy,
    review_output,
)

# Synthetic, fabricated identifier-shaped tokens (not real people or data).
FAKE_EMAIL = "user@example.com"
FAKE_SSN = "123-45-6789"
FAKE_PHONE = "555-000-1111"
FAKE_IP = "10.0.0.1"


def test_pii_detector_flags_and_redacts_known_shapes():
    result = detect_pii(f"contact {FAKE_EMAIL} ssn {FAKE_SSN} ip {FAKE_IP}")
    assert set(["email", "ssn", "ip"]).issubset(set(result.pii_types))
    assert result.redaction_applied is True
    assert FAKE_EMAIL not in result.redacted_text
    assert FAKE_SSN not in result.redacted_text
    assert "[REDACTED_EMAIL]" in result.redacted_text


def test_pii_detector_returns_clean_for_plain_text():
    result = detect_pii("the purple widget hums quietly")
    assert result.pii_types == []
    assert result.redaction_applied is False


def test_distress_detector_matches_synthetic_indicator():
    result = detect_distress(
        "zzz synthetic distress token qqq",
        extra_indicators=["synthetic distress token"],
    )
    assert result.escalation_detected is True
    assert "synthetic distress token" in result.matched_indicators


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


def test_output_review_flags_leak_and_human_claim():
    result = review_output(
        f"your number {FAKE_PHONE} and a human will contact you",
        input_pii_types=["phone"],
    )
    assert "phone" in result.pii_leaked_types
    assert result.human_escalation_claimed is True


def test_output_review_flags_integrator_boundary_phrase():
    result = review_output(
        "this reply contains a synthetic boundary marker",
        policy={"output_boundary_phrases": ["synthetic boundary marker"]},
    )
    assert "synthetic boundary marker" in result.policy_boundary_hits


def test_registry_exposes_four_detectors():
    assert set(DETECTORS) == {"pii", "distress", "policy", "output_review"}
