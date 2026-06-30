"""Tests for shadow report aggregation over synthetic turn payloads."""

import json
import pathlib

import pytest

from saski_shadow import PublicOutcome, aggregate_shadow_report, load_turns_jsonl
from saski_shadow.aggregate.report import (
    COMPLIANCE_DISCLAIMER,
    ESCALATION_DISCLAIMER,
    UPGRADE_MESSAGE,
    _split_laws_by_effective_date,
    main,
)
from saski_shadow.laws import LAW_SET_VERSION, STARTER_LAWS

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
    assert len(report["sections"]) == 9


def test_absent_governance_tier_defaults_to_tier_clean():
    turn = {"turn_index": 0, "session_id": "sess_test_001", "engine_summary": {"outcome": "allow"}}
    report = aggregate_shadow_report([turn])
    measured = report["sections"]["token_savings_calculation"]["measured_from_shadow"]
    assert measured["tier_clean_turns"] == 1


def test_by_outcome_uses_public_outcome_vocabulary_only():
    report = aggregate_shadow_report(_sample_turns())
    by_outcome = report["sections"]["escalation_signal_count"]["by_outcome"]
    assert set(by_outcome) == {o.value for o in PublicOutcome}


def test_unsafe_flow_categories_are_the_eight_neutral_values():
    report = aggregate_shadow_report(_sample_turns())
    categories = report["sections"]["unsafe_flow_documentation"]["categories"]
    assert set(categories) == {
        "enforcement_would_block",
        "policy_boundary_failure",
        "content_sanitization_gap",
        "integrator_override",
        "manual_review_required",
        "adversarial_probe",
        "clinical_intent_boundary",
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
    # No integrator inputs supplied -> nothing is invented.
    section = aggregate_shadow_report(_sample_turns())["sections"]["token_savings_calculation"]
    assert section["basis"] == "insufficient_inputs"
    assert section["savings"] == {
        "tokens_saved_estimate": None,
        "tier_clean_tokens_saved": None,
        "tier_warning_tokens_saved": None,
        "tier_escalation_tokens_saved": None,
    }
    assert section["prospect_inputs"]["legacy_system_prompt_tokens"] is None
    assert section["prospect_inputs"]["lean_product_prompt_tokens"] is None
    # Observed counts are still reported even without a model.
    assert section["measured_from_shadow"]["total_turns"] == 4
    assert section["measured_from_shadow"]["would_have_blocked_turns"] == 1


def test_token_savings_calculates_when_inputs_supplied():
    # 4 turns (no regulated mode): 1 clean, 1 warning, 2 escalation.
    prospect_inputs = {
        "legacy_system_prompt_tokens": 450,
        "lean_product_prompt_tokens": 103,
    }
    section = aggregate_shadow_report(
        _sample_turns(), prospect_inputs=prospect_inputs
    )["sections"]["token_savings_calculation"]

    assert section["basis"] == "estimated_from_integrator_inputs"
    # clean: 450-103=347; warning: 450-(103+50)=297; escalation: 450 each (LLM not called).
    savings = section["savings"]
    assert savings["tier_clean_tokens_saved"] == 347.0
    assert savings["tier_warning_tokens_saved"] == 297.0
    assert savings["tier_escalation_tokens_saved"] == 900.0
    assert savings["tokens_saved_estimate"] == 1544.0
    assert section["token_model"] == {
        "regulated_modes": ["child", "patient", "therapist"],
        "regulated_mode_floor_tokens": 85.0,
        "warning_append_tokens": 50.0,
        "tier3_llm_tokens": 0,
    }
    assert section["prospect_inputs"] == {
        "legacy_system_prompt_tokens": 450.0,
        "lean_product_prompt_tokens": 103.0,
    }
    # No dollar figure is ever computed.
    assert "dollar_savings_note" in section
    assert "tokens_saved" in section["dollar_savings_note"]


def test_token_savings_applies_regulated_mode_floor_per_turn():
    # Two clean turns in patient mode -> 85-token floor added on top of lean.
    turns = [
        _turn(0, "sess_reg", outcome="allow", tier="tier_clean"),
        _turn(1, "sess_reg", outcome="allow", tier="tier_clean"),
    ]
    for turn in turns:
        turn["engine_summary"]["mode"] = "patient"
    section = aggregate_shadow_report(
        turns,
        prospect_inputs={
            "legacy_system_prompt_tokens": 450,
            "lean_product_prompt_tokens": 103,
        },
    )["sections"]["token_savings_calculation"]
    # each clean regulated turn: 450 - (103 + 85) = 262
    assert section["savings"]["tier_clean_tokens_saved"] == 524.0
    assert section["savings"]["tokens_saved_estimate"] == 524.0
    assert section["measured_from_shadow"]["regulated_mode_turns"] == 2


def test_token_savings_floor_and_warning_overrides_honored():
    turns = [_turn(0, "s", outcome="allow", tier="tier_clean")]
    turns[0]["engine_summary"]["mode"] = "child"
    section = aggregate_shadow_report(
        turns,
        prospect_inputs={
            "legacy_system_prompt_tokens": 1000,
            "lean_product_prompt_tokens": 100,
            "regulated_mode_floor_tokens": 0,
            "warning_append_tokens": 0,
        },
    )["sections"]["token_savings_calculation"]
    assert section["token_model"]["regulated_mode_floor_tokens"] == 0.0
    assert section["token_model"]["warning_append_tokens"] == 0.0
    # Floor override of 0 -> regulated turn behaves like a plain clean turn.
    assert section["savings"]["tier_clean_tokens_saved"] == 900.0


def test_token_savings_never_negative():
    # Lean model costlier than legacy -> Tier 1/2 clamp to 0; Tier 3 still saves.
    section = aggregate_shadow_report(
        _sample_turns(),
        prospect_inputs={
            "legacy_system_prompt_tokens": 100,
            "lean_product_prompt_tokens": 500,
        },
    )["sections"]["token_savings_calculation"]
    assert section["savings"]["tier_clean_tokens_saved"] == 0.0
    assert section["savings"]["tier_warning_tokens_saved"] == 0.0
    assert section["savings"]["tier_escalation_tokens_saved"] == 200.0
    assert section["savings"]["tokens_saved_estimate"] == 200.0


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
    assert {
        "law_id",
        "jurisdiction",
        "domains",
        "matched_domains",
        "domain",
        "citation",
        "effective_date",
        "date_added",
        "note",
    }.issubset(set(first))


def test_section2_surfaces_tier2_federal_laws_via_prefix_match():
    # Federal ("US") entries must reach a generated report for any US-prefixed
    # turn in the relevant domain, alongside the state-specific matches.
    turns = [
        _turn(0, "sess_test_001", jurisdiction="US-CA", domain="employment"),
        _turn(1, "sess_test_002", jurisdiction="US-CA", domain="healthcare"),
    ]
    section = aggregate_shadow_report(turns)["sections"]["compliance_exposure_examples"]
    unique = set(section["law_match_summary"]["unique_law_ids"])
    # US-CA employment turn surfaces federal employment entries.
    assert {"US-ADEA", "US-FCRA"}.issubset(unique)
    # US-CA healthcare turn surfaces federal healthcare entries beside HIPAA.
    assert {
        "US-HIPAA",
        "US-FTC-HBNR",
        "US-42-CFR-PART-2",
        "US-ACA-1557",
    }.issubset(unique)


def test_section2_says_so_plainly_when_no_metadata_supplied():
    section = aggregate_shadow_report(_sample_turns())["sections"]["compliance_exposure_examples"]
    assert section["matched_laws"] == []
    assert "No jurisdiction/domain metadata" in section["law_match_summary"]["no_match_statement"]


def test_section2_no_match_when_metadata_present_but_nothing_matches():
    # Non-US jurisdiction: metadata is present but nothing in the US-only
    # starter set matches (federal "US" laws do not apply outside the US).
    turns = [_turn(0, "sess_test_001", jurisdiction="GB", domain="consumer_chatbot")]
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
    matched_ids = {law["law_id"] for law in example["matched_laws"]}
    assert "US-UT-MENTAL-HEALTH-CHATBOT" in matched_ids
    assert example["observed_signals"]["baseline_pii_signal"] is True


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
                    "legacy_system_prompt_tokens": 450,
                    "lean_product_prompt_tokens": 103,
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
    assert section["savings"]["tokens_saved_estimate"] is not None


# --- Task 2: future-effective law split -------------------------------------


def test_split_helper_classifies_past_null_and_future():
    laws = [
        {"law_id": "PAST", "effective_date": "2020-01-01"},
        {"law_id": "NULL", "effective_date": ""},
        {"law_id": "FUTURE", "effective_date": "2999-01-01"},
    ]
    in_force, future = _split_laws_by_effective_date(laws, "2026-06-24")
    in_force_ids = {law["law_id"] for law in in_force}
    future_ids = {law["law_id"] for law in future}
    assert in_force_ids == {"PAST", "NULL"}
    assert future_ids == {"FUTURE"}


def test_section2_has_both_buckets_even_when_one_empty():
    section = aggregate_shadow_report(_sample_turns())["sections"]["compliance_exposure_examples"]
    by_status = section["matched_laws_by_status"]
    assert set(by_status) == {"in_force", "future_effective"}
    assert by_status["in_force"] == []
    assert by_status["future_effective"] == []
    assert section["law_match_summary"]["future_effective_count"] == 0


def test_section2_future_effective_partitions_matched_laws_without_dropping():
    # Real laws across several jurisdictions/domains; every matched law must
    # land in exactly one bucket, and future-dated laws only in future_effective.
    turns = [
        _turn(0, "s1", jurisdiction="US-TN", domain="mental_health"),
        _turn(1, "s2", jurisdiction="US-CA", domain="healthcare"),
    ]
    report = aggregate_shadow_report(turns)
    section = report["sections"]["compliance_exposure_examples"]
    today = report["generated_at_utc"][:10]

    flat_ids = {law["law_id"] for law in section["matched_laws"]}
    in_force = section["matched_laws_by_status"]["in_force"]
    future = section["matched_laws_by_status"]["future_effective"]
    in_ids = {law["law_id"] for law in in_force}
    fut_ids = {law["law_id"] for law in future}

    # No law dropped, no law double-counted across buckets.
    assert in_ids | fut_ids == flat_ids
    assert in_ids.isdisjoint(fut_ids)
    assert section["law_match_summary"]["future_effective_count"] == len(future)
    # Every future_effective law genuinely has a date after report generation.
    assert all(law["effective_date"] > today for law in future)


# --- Task 3: multi-domain wiring through the report pipeline -----------------


def test_section2_multi_domain_turn_surfaces_both_domain_buckets():
    turn = {
        "turn_index": 0,
        "session_id": "sess_child",
        "jurisdiction": "US",
        "domains": ["consumer_chatbot", "csam"],
        "engine_summary": {"outcome": "allow"},
    }
    section = aggregate_shadow_report([turn])["sections"]["compliance_exposure_examples"]
    unique = set(section["law_match_summary"]["unique_law_ids"])
    assert "US-COPPA" in unique  # consumer_chatbot
    assert any("csam" in law["matched_domains"] for law in section["matched_laws"])


def test_section2_mode_only_turn_derives_domains_and_matches_laws():
    turn = {
        "turn_index": 0,
        "session_id": "sess_mh",
        "jurisdiction": "US-NY",
        "engine_summary": {
            "outcome": "allow",
            "mode": "mental_health_support",
            "domains": ["mental_health", "consumer_chatbot"],
            "domains_source": "mode_derived",
        },
    }
    section = aggregate_shadow_report([turn])["sections"]["compliance_exposure_examples"]
    assert section["law_match_summary"]["turns_with_law_match"] == 1
    law = next(law for law in section["matched_laws"] if law["law_id"] == "US-NY-AI-COMPANION")
    assert law["domains"] == ["consumer_chatbot", "mental_health"]
    assert set(law["matched_domains"]) == {"consumer_chatbot", "mental_health"}


def test_section2_mode_only_turn_via_report_mode_fallback():
    # JSONL with mode but no explicit domain fields — report derives like analyze_turn.
    turn = {
        "turn_index": 0,
        "session_id": "sess_mh_fallback",
        "jurisdiction": "US-NY",
        "engine_summary": {
            "outcome": "allow",
            "mode": "mental_health_support",
        },
    }
    section = aggregate_shadow_report([turn])["sections"]["compliance_exposure_examples"]
    assert section["law_match_summary"]["turns_with_law_match"] == 1
    assert any(
        law.get("matched_domains") for law in section["matched_laws"]
    )


# --- Task 4: report credibility additions -----------------------------------


def test_methodology_block_present_with_all_keys():
    report = aggregate_shadow_report(_sample_turns())
    methodology = report["methodology"]
    assert set(methodology) == {
        "detector_profile",
        "law_set_version",
        "law_set_sync_date",
        "total_laws_evaluated",
        "total_jurisdictions",
        "schema_version",
        "report_period",
    }
    assert methodology["detector_profile"] == "baseline-v1"
    assert methodology["law_set_version"] == LAW_SET_VERSION
    assert methodology["total_laws_evaluated"] == len(STARTER_LAWS)
    assert set(methodology["report_period"]) == {"start_utc", "end_utc"}


def test_detection_limitations_in_sections_two_five_and_six():
    sections = aggregate_shadow_report(_sample_turns())["sections"]
    for name in (
        "compliance_exposure_examples",
        "escalation_signal_count",
        "unsafe_flow_documentation",
    ):
        limitations = sections[name]["detection_limitations"]
        assert isinstance(limitations, list) and limitations
        assert any("CSAM" in item for item in limitations)


def test_baseline_only_caveat_appears_when_section_count_is_zero():
    # Clean turns: no PII, no escalation, no jurisdiction/domain metadata.
    clean = [_turn(0, "s"), _turn(1, "s")]
    sections = aggregate_shadow_report(clean)["sections"]
    assert "baseline_only_caveat" in sections["pii_phi_detection_summary"]
    assert "baseline_only_caveat" in sections["compliance_exposure_examples"]
    assert "baseline_only_caveat" in sections["escalation_signal_count"]


def test_baseline_only_caveat_absent_when_section_count_nonzero():
    # _sample_turns has one PII turn and one escalation turn.
    sections = aggregate_shadow_report(_sample_turns())["sections"]
    assert "baseline_only_caveat" not in sections["pii_phi_detection_summary"]
    assert "baseline_only_caveat" not in sections["escalation_signal_count"]


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
            "legacy_system_prompt_tokens": 450,
            "lean_product_prompt_tokens": 103,
        },
        latency_targets={"integrator_p95_target_ms": 50.0},
    )
    # Raises jsonschema.ValidationError if report and schema ever drift apart.
    jsonschema.validate(instance=report, schema=schema)


def test_section2_disclaimer_states_metadata_keyed_matching():
    section = aggregate_shadow_report(_sample_turns())["sections"]["compliance_exposure_examples"]
    assert "integrator-supplied jurisdiction and domain metadata" in section["disclaimer"]
    assert "integrator-supplied jurisdiction and domain metadata" in COMPLIANCE_DISCLAIMER


def test_section3_disclaimer_states_observation_only_and_no_dollars():
    section = aggregate_shadow_report(_sample_turns())["sections"]["token_savings_calculation"]
    disclaimer = section["disclaimer"]
    assert "shadow observed, it did not act" in disclaimer
    assert "Dollar savings are never computed here" in disclaimer


def test_section5_escalation_disclaimer_is_clean_and_unchanged():
    section = aggregate_shadow_report(_sample_turns())["sections"]["escalation_signal_count"]
    assert "not clinical crisis detection" in section["disclaimer"]
    assert ESCALATION_DISCLAIMER == (
        "Escalation counts reflect baseline distress phrase-list matches only and are "
        "not clinical crisis detection."
    )


def test_adversarial_probe_in_unsafe_flows_when_signal_fires():
    turn = _turn(0, "sess_adv")
    turn["engine_summary"]["adversarial_signal"] = True
    turn["engine_summary"]["adversarial_matches"] = ["jailbreak_phrase"]
    flows = aggregate_shadow_report([turn])["sections"]["unsafe_flow_documentation"]
    items = flows["categories"]["adversarial_probe"]
    assert len(items) == 1
    assert items[0]["signals"]["adversarial_matches"] == ["jailbreak_phrase"]


def test_clinical_intent_boundary_in_unsafe_flows_when_signal_fires():
    turn = _turn(0, "sess_clin")
    turn["engine_summary"]["clinical_intent_signal"] = True
    turn["engine_summary"]["clinical_intent_matches"] = ["diagnosis_request"]
    flows = aggregate_shadow_report([turn])["sections"]["unsafe_flow_documentation"]
    items = flows["categories"]["clinical_intent_boundary"]
    assert len(items) == 1
    assert items[0]["signals"]["clinical_intent_matches"] == ["diagnosis_request"]


def test_next_steps_derived_from_session_signals():
    turns = [
        _turn(0, "s", pii=True, pii_types=["email"]),
        _turn(1, "s", escalation=True),
    ]
    turn = _turn(2, "s")
    turn["engine_summary"]["clinical_intent_signal"] = True
    turns.append(turn)
    next_steps = aggregate_shadow_report(turns)["sections"]["recommended_path"]["next_steps"]
    assert "Integrator-defined next step" not in next_steps
    assert any("Clinical boundary requests detected" in step for step in next_steps)
    assert any("Distress signals detected" in step for step in next_steps)
    assert any("PII detected in user messages" in step for step in next_steps)


def test_next_steps_always_includes_contact_line():
    report = aggregate_shadow_report([_turn(0, "sess_clean")])
    next_steps = report["sections"]["recommended_path"]["next_steps"]
    assert any("info@techviz.us" in step for step in next_steps)
