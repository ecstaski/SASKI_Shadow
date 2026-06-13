"""Tests for turn payloads, bundles, and the strict export boundary."""

import pytest

from saski_shadow import (
    build_evidence_bundle,
    record_research_event,
    turn_payload_from_result,
    update_bundle_outcome,
)
from saski_shadow.evidence import infer_export_action_label, map_public_outcome
from saski_shadow.enums import PublicOutcome

HEX64_A = "a" * 64
HEX64_B = "b" * 64
HEX64_C = "c" * 64


class StubResult:
    def __init__(self, should_block=False, action="allow", pii_detected=False, metadata=None, envelope=None):
        self.should_block = should_block
        self.action = action
        self.is_crisis = False
        self.pii_detected = pii_detected
        self.envelope = envelope
        self.policy_id = "policy_test"
        self.policy_hash = HEX64_B
        self.pipeline_ms = 0.0
        self.processing_time_ms = 0.0
        self.model_id = None
        self.provider_id = None
        self.metadata = metadata

    def get_audit_record(self):
        return {"risk_band": "low"}


def _strict_turn(**overrides):
    turn = {
        "run_id": "run_test_0",
        "session_id": "sess_test_001",
        "policy_hash": HEX64_B,
        "input_hash": HEX64_A,
        "output_hash": HEX64_C,
        "mode_tag": "shadow_mode",
        "timestamp_ms": 1,
        "action_label": "PASS_CLEAN",
        "turn_index": 0,
    }
    turn.update(overrides)
    return turn


def test_turn_payload_defaults_to_saski_on_mode_tag():
    payload = turn_payload_from_result(StubResult(), turn_index=0, session_id="sess_test_001")
    assert payload["mode_tag"] == "saski_on"


def test_turn_payload_is_hash_only_and_carries_identity():
    envelope = {"run_id": "run_test_0", "input_hash": HEX64_A, "output_hash": HEX64_C}
    payload = turn_payload_from_result(
        StubResult(envelope=envelope),
        turn_index=2,
        session_id="sess_test_001",
        mode_tag="shadow_mode",
    )
    assert payload["input_hash"] == HEX64_A
    assert payload["run_id"] == "run_test_0"
    assert payload["session_id"] == "sess_test_001"


def test_bundle_checksum_is_order_independent_of_input():
    turn_a = _strict_turn(turn_index=0, timestamp_ms=1)
    turn_b = _strict_turn(turn_index=1, timestamp_ms=2, run_id="run_test_1")
    first = build_evidence_bundle("sess_test_001", [turn_a, turn_b])
    second = build_evidence_bundle("sess_test_001", [turn_b, turn_a])
    assert first["integrity_checksum"] == second["integrity_checksum"]
    assert first["turn_count"] == 2


def test_strict_boundary_rejects_raw_text_keys():
    bad_turn = _strict_turn(prompt="some text")
    with pytest.raises(ValueError):
        build_evidence_bundle("sess_test_001", [bad_turn], strict_export_boundary=True)


def test_strict_boundary_requires_identity_keys():
    incomplete = _strict_turn()
    del incomplete["input_hash"]
    with pytest.raises(ValueError):
        build_evidence_bundle("sess_test_001", [incomplete], strict_export_boundary=True)


def test_research_event_produces_strict_bundle_without_raw_text():
    bundle = record_research_event("alpha", "beta", "shadow_mode", "sess_test_001")
    assert bundle["turn_count"] == 1
    turn = bundle["turns"][0]
    assert "prompt" not in turn and "completion" not in turn
    assert turn["input_hash"] and turn["output_hash"]


def test_update_bundle_outcome_accepts_valid_status():
    payload = update_bundle_outcome("run_test_0", "Resolved", True)
    assert payload["status"] == "Resolved"
    assert payload["corrective_action_taken"] is True


def test_update_bundle_outcome_rejects_unknown_status():
    with pytest.raises(ValueError):
        update_bundle_outcome("run_test_0", "NotAStatus", False)


def test_public_outcome_mapping_for_plain_actions():
    assert map_public_outcome(StubResult(action="allow")) is PublicOutcome.ALLOW
    assert map_public_outcome(StubResult(action="block")) is PublicOutcome.BLOCK


def test_action_label_reflects_block_monitor_and_rewrite():
    assert infer_export_action_label(StubResult(should_block=True, action="block")) == "BLOCK_SAFETY"
    assert infer_export_action_label(StubResult(action="warn")) == "PASS_WITH_MONITOR"
    assert infer_export_action_label(StubResult(pii_detected=True)) == "REWRITE_SENSITIVE"
    assert infer_export_action_label(StubResult()) == "PASS_CLEAN"
