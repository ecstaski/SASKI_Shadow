"""Tests for shadow report aggregation over synthetic turn payloads."""

import json
import pathlib

import pytest

from saski_shadow import PublicOutcome, aggregate_shadow_report, load_turns_jsonl
from saski_shadow.aggregate.report import (
    COMPLIANCE_DISCLAIMER,
    ESCALATION_DISCLAIMER,
    UPGRADE_MESSAGE,
    main,
)

HEX64_A = "a" * 64
SCHEMA_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "saski_shadow"
    / "schemas"
    / "shadow_report_v1.json"
)


def _turn(idx, session_id, *, outcome="allow", tier="tier_clean", pii=False,
          escalation=False, would_block=False, pii_types=None, latency=1.0,
          jurisdiction=None, domain=None):
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
            "user_jurisdiction": jurisdiction,
            "domain": domain,
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


def test_detected_pii_types_map_to_named_buckets_not_other():
    # Every category the baseline detector can emit must have its own bucket;
    # none should silently fall into "other". 'ip' previously regressed here.
    turns = [
        _turn(0, "s", pii=True, pii_types=["ip"]),
        _turn(1, "s", pii=True, pii_types=["ssn"]),
        _turn(2, "s", pii=True, pii_types=["credit_card"]),
    ]
    by_type = aggregate_shadow_report(turns)["sections"]["pii_phi_detection_summary"]["by_pii_type"]
    assert by_type["ip"] == 1
    assert by_type["ssn"] == 1
    assert by_type["credit_card"] == 1
    assert by_type["other"] == 0


def test_token_savings_nulls_when_inputs_missing():
    # No token model / pricing supplied -> nothing is invented.
    section = aggregate_shadow_report(_sample_turns())["sections"]["token_savings_calculation"]
    assert section["basis"] == "insufficient_inputs"
    assert section["savings"] == {
        "tokens_saved_per_session_estimate": None,
        "monthly_tokens_saved_estimate": None,
        "annual_usd_saved_estimate": None,
    }
    assert section["token_model"]["legacy_system_tokens_per_turn"] is None
    # Observed counts are still reported even without a model.
    assert section["measured_from_shadow"]["total_turns"] == 4
    assert section["measured_from_shadow"]["blocked_llm_turns"] == 1


def test_token_savings_calculates_when_inputs_supplied():
    # 4 turns: 1 clean, 1 warning, 2 escalation (1 of which blocked).
    prospect_inputs = {
        "legacy_system_tokens_per_turn": 400,
        "governed_system_tokens_per_turn": 120,
        "warning_append_tokens": 30,
        "regulated_floor_tokens": 200,
        "avg_llm_turns_per_session": 8,
        "monthly_sessions": 100000,
        "input_price_per_1m_tokens_usd": 2.5,
    }
    section = aggregate_shadow_report(
        _sample_turns(), prospect_inputs=prospect_inputs
    )["sections"]["token_savings_calculation"]

    assert section["basis"] == "estimated_from_integrator_inputs"
    # governed_total = 1*120 + 1*150 + 2*200 = 670; legacy_total = 4*400 = 1600
    # saved_total = 930; per_turn = 232.5; per_session = 232.5 * 8 = 1860
    savings = section["savings"]
    assert savings["tokens_saved_per_session_estimate"] == 1860.0
    assert savings["monthly_tokens_saved_estimate"] == 186_000_000.0
    assert savings["annual_usd_saved_estimate"] == 5580.0
    assert section["token_model"] == {
        "legacy_system_tokens_per_turn": 400.0,
        "governed_system_tokens_per_turn": 120.0,
        "warning_append_tokens": 30.0,
        "regulated_floor_tokens": 200.0,
    }


def test_token_savings_defaults_warning_zero_and_floor_to_governed():
    prospect_inputs = {
        "legacy_system_tokens_per_turn": 400,
        "governed_system_tokens_per_turn": 120,
    }
    section = aggregate_shadow_report(
        _sample_turns(), prospect_inputs=prospect_inputs
    )["sections"]["token_savings_calculation"]
    assert section["basis"] == "estimated_from_integrator_inputs"
    assert section["token_model"]["warning_append_tokens"] == 0.0
    assert section["token_model"]["regulated_floor_tokens"] == 120.0
    # Without avg_llm_turns_per_session, per-session savings cannot be derived.
    assert section["savings"]["tokens_saved_per_session_estimate"] is None


def test_token_savings_never_negative():
    # Governed model costlier than legacy -> savings clamp to 0, not negative.
    prospect_inputs = {
        "legacy_system_tokens_per_turn": 100,
        "governed_system_tokens_per_turn": 500,
        "avg_llm_turns_per_session": 4,
    }
    section = aggregate_shadow_report(
        _sample_turns(), prospect_inputs=prospect_inputs
    )["sections"]["token_savings_calculation"]
    assert section["savings"]["tokens_saved_per_session_estimate"] == 0.0


def test_section2_names_specific_laws_on_jurisdiction_domain_match():
    turns = [
        _turn(0, "sess_test_001", jurisdiction="US-CA", domain="healthcare"),
        _turn(1, "sess_test_002", jurisdiction="US-NY-NYC", domain="employment"),
    ]
    section = aggregate_shadow_report(turns)["sections"]["compliance_exposure_examples"]
    unique = set(section["law_match_summary"]["unique_law_ids"])
    assert {"US-CA-AB3030-HEALTH", "US-CA-HEALTH-ADVICE-AI"}.issubset(unique)
    assert "US-NYC-AEDT" in unique
    assert section["law_match_summary"]["no_match_statement"] is None
    # Each matched law carries fact-only fields including the citation.
    first = section["matched_laws"][0]
    assert set(first) == {
        "law_id", "jurisdiction", "domain", "citation", "effective_date", "date_added", "note"
    }


def test_section2_says_so_plainly_when_no_metadata_supplied():
    section = aggregate_shadow_report(_sample_turns())["sections"]["compliance_exposure_examples"]
    assert section["matched_laws"] == []
    assert "No jurisdiction/domain metadata" in section["law_match_summary"]["no_match_statement"]


def test_section2_no_match_when_metadata_present_but_nothing_matches():
    turns = [_turn(0, "sess_test_001", jurisdiction="US-ZZ", domain="consumer_chatbot")]
    section = aggregate_shadow_report(turns)["sections"]["compliance_exposure_examples"]
    assert section["matched_laws"] == []
    assert section["law_match_summary"]["turns_with_jurisdiction_metadata"] == 1
    assert "did not" in section["law_match_summary"]["no_match_statement"] or \
        "No laws" in section["law_match_summary"]["no_match_statement"]


def test_section2_disclaimer_states_starter_set_and_no_private_logic():
    section = aggregate_shadow_report(_sample_turns())["sections"]["compliance_exposure_examples"]
    assert "starter set of laws" in section["disclaimer"]
    assert "does not apply private SASKI enforcement" in section["disclaimer"]


def test_section2_example_attaches_signals_as_context_not_as_match_key():
    # PII present but matching still depends only on jurisdiction + domain.
    turns = [
        _turn(0, "sess_test_001", pii=True, pii_types=["email"],
              jurisdiction="US-UT", domain="mental_health"),
    ]
    section = aggregate_shadow_report(turns)["sections"]["compliance_exposure_examples"]
    example = section["examples"][0]
    assert example["matched_laws"][0]["law_id"] == "US-UT-MENTAL-HEALTH-CHATBOT"
    assert example["observed_signals"]["pii_detected"] is True


def test_load_turns_jsonl_round_trip(tmp_path):
    path = tmp_path / "turns.jsonl"
    turns = _sample_turns()
    with open(path, "w", encoding="utf-8") as handle:
        for turn in turns:
            handle.write(json.dumps(turn) + "\n")
        handle.write("\n")  # blank line should be skipped
    loaded = load_turns_jsonl(str(path))
    assert len(loaded) == len(turns)


def test_cli_aggregate_with_config_populates_token_savings(tmp_path):
    input_path = tmp_path / "turns.jsonl"
    output_path = tmp_path / "report.json"
    config_path = tmp_path / "pricing.json"

    with open(input_path, "w", encoding="utf-8") as handle:
        for turn in _sample_turns():
            handle.write(json.dumps(turn) + "\n")
    config_path.write_text(
        json.dumps(
            {
                "prospect_inputs": {
                    "legacy_system_tokens_per_turn": 400,
                    "governed_system_tokens_per_turn": 120,
                    "warning_append_tokens": 30,
                    "regulated_floor_tokens": 200,
                    "avg_llm_turns_per_session": 8,
                    "monthly_sessions": 100000,
                    "input_price_per_1m_tokens_usd": 2.5,
                }
            }
        ),
        encoding="utf-8",
    )

    rc = main(
        [
            "aggregate",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--config",
            str(config_path),
        ]
    )
    assert rc == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    section = report["sections"]["token_savings_calculation"]
    assert section["basis"] == "estimated_from_integrator_inputs"
    assert section["savings"]["annual_usd_saved_estimate"] == 5580.0


def test_generated_report_validates_against_bundled_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    turns = [
        _turn(0, "sess_test_001", pii=True, pii_types=["ip"],
              jurisdiction="US-CA", domain="healthcare"),
        _turn(1, "sess_test_002", outcome="block", tier="tier_escalation", would_block=True),
    ]
    report = aggregate_shadow_report(
        turns,
        prospect_inputs={
            "legacy_system_tokens_per_turn": 400,
            "governed_system_tokens_per_turn": 120,
            "avg_llm_turns_per_session": 8,
            "monthly_sessions": 1000,
            "input_price_per_1m_tokens_usd": 2.5,
        },
        latency_targets={"integrator_p95_target_ms": 50.0},
    )
    # Raises jsonschema.ValidationError if report and schema ever drift apart.
    jsonschema.validate(instance=report, schema=schema)
