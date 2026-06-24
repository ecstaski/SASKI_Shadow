"""Axis 2 - detection tests (text -> PII + distress) and end-to-end coverage.

Exercises the real detectors on realistic synthetic input, plus domain coverage
(gap 2) and mode coverage (gap 3) through ``analyze_turn``.
"""

from __future__ import annotations

from saski_shadow.analyzer import analyze_turn
from saski_shadow.detectors import detect_distress, detect_pii
from saski_shadow.laws import match_laws

# 4242 4242 4242 4242 is a publicly known Luhn-valid test card number.
_PHI_TEXT = (
    "My SSN is 123-45-6789, card 4242 4242 4242 4242, "
    "Member ID: ABC123456, call me at (415) 555-0132."
)

_MODES = [
    "child",
    "student",
    "patient",
    "therapist",
    "mental_health_support",
    "wellness_coaching",
    "career_coaching",
    "sports_coaching",
    "business",
    "general_assistant",
    "hr_recruiting",
    "default",
]

# domain -> (jurisdiction, message) for end-to-end domain coverage.
_DOMAIN_CASES = {
    "consumer_chatbot": ("US-CA", "How do I stay safe chatting with strangers online?"),
    "csam": ("US", "A stranger online keeps pressuring me and it makes me uncomfortable."),
    "employment": ("US-NY-NYC", "Please rank these job applicants by their resumes."),
    "healthcare": ("US-CA", _PHI_TEXT),
    "mental_health": ("US-NV", "I have been feeling low and unmotivated lately."),
}


# --- PII detection ----------------------------------------------------------


def test_pii_detects_each_expected_type_in_synthetic_phi():
    result = detect_pii(_PHI_TEXT)
    for ptype in ("ssn", "credit_card", "insurance_id", "phone"):
        assert ptype in result.pii_types, f"missing {ptype} in {result.pii_types}"
    assert result.redaction_applied is True


def test_pii_clean_message_reports_no_pii():
    result = detect_pii("the purple widget hums quietly")
    assert result.pii_types == []
    assert result.redaction_applied is False


# --- Distress detection -----------------------------------------------------


def test_distress_extra_indicators_fire_on_matching_phrases():
    result = detect_distress(
        "I want to hurt myself and I feel hopeless",
        extra_indicators=["want to hurt", "feel hopeless"],
    )
    assert result.escalation_detected is True
    assert set(result.matched_indicators) == {"want to hurt", "feel hopeless"}


def test_distress_word_boundary_precision_sad_does_not_fire_on_saddleback():
    result = detect_distress("Saddleback mountain trail", extra_indicators=["sad"])
    assert result.escalation_detected is False


def test_distress_baseline_without_extra_indicators_misses_realistic_language():
    # Baseline limitation, made explicit: only the synthetic placeholder tokens
    # fire out of the box; realistic distress language does not match unless the
    # integrator supplies real indicators.
    placeholder = detect_distress("payload synthetic-distress-token-alpha here")
    realistic = detect_distress("I feel hopeless and I want to give up")
    assert placeholder.escalation_detected is True
    assert realistic.escalation_detected is False


# --- Gap 2: domain coverage end-to-end through analyze_turn ------------------


def test_each_domain_flows_through_analyze_turn():
    for domain, (jurisdiction, message) in _DOMAIN_CASES.items():
        result = analyze_turn(
            message,
            session_context={"user_jurisdiction": jurisdiction, "domain": domain},
        )
        summary = result.metadata["engine_summary"]
        assert summary["domain"] == domain
        assert summary["user_jurisdiction"] == jurisdiction


def test_healthcare_domain_detects_pii_on_synthetic_phi():
    jurisdiction, message = _DOMAIN_CASES["healthcare"]
    result = analyze_turn(
        message,
        session_context={"user_jurisdiction": jurisdiction, "domain": "healthcare"},
    )
    assert result.pii_detected is True
    assert "ssn" in result.metadata["engine_summary"]["pii_types"]


def test_csam_and_employment_surface_domain_laws_via_result_passthrough():
    # Law matching uses the result's jurisdiction/domain passthrough, never tag
    # injection.
    for domain in ("csam", "employment"):
        jurisdiction, message = _DOMAIN_CASES[domain]
        result = analyze_turn(
            message,
            session_context={"user_jurisdiction": jurisdiction, "domain": domain},
        )
        summary = result.metadata["engine_summary"]
        matched = match_laws(summary["user_jurisdiction"], summary["domain"])
        assert matched, f"no laws surfaced for {domain}"
        assert all(law["domain"] == domain for law in matched)


# --- Gap 3: mode coverage ---------------------------------------------------


def test_every_mode_is_recorded_on_the_result():
    for mode in _MODES:
        result = analyze_turn("the purple widget hums quietly", mode=mode)
        assert result.mode == mode
        assert result.metadata["engine_summary"]["mode"] == mode


def test_unrecognized_mode_falls_back_to_none():
    result = analyze_turn("the purple widget hums quietly", mode="not_a_real_mode")
    assert result.mode is None
