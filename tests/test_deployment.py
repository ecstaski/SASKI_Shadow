"""Tests for deployment gating behavior."""

import pytest

from saski_shadow import DeploymentMode, evaluate_deployment_mode


class StubResult:
    """Minimal stub satisfying the parts of AnalysisResult used by gating."""

    def __init__(self, should_block=False, action="allow"):
        self.should_block = should_block
        self.action = action
        self.is_crisis = False
        self.pii_detected = False
        self.envelope = None
        self.policy_id = None
        self.policy_hash = None
        self.pipeline_ms = 0.0
        self.processing_time_ms = 0.0
        self.model_id = None
        self.provider_id = None
        self.metadata = None

    def get_audit_record(self):
        return {}


def test_enforce_mode_passes_block_through():
    decision = evaluate_deployment_mode(StubResult(should_block=True), DeploymentMode.ENFORCE)
    assert decision.effective_should_block is True
    assert decision.enforcement_suppressed is False
    assert decision.warn_user is False


def test_shadow_mode_suppresses_enforcement():
    decision = evaluate_deployment_mode(StubResult(should_block=True), "shadow")
    assert decision.effective_should_block is False
    assert decision.enforcement_suppressed is True
    assert decision.warn_user is False


def test_warn_mode_warns_without_enforcing():
    decision = evaluate_deployment_mode(StubResult(should_block=True), "warn")
    assert decision.effective_should_block is False
    assert decision.enforcement_suppressed is True
    assert decision.warn_user is True


def test_clean_result_never_blocks_in_any_mode():
    for mode in ("enforce", "shadow", "warn"):
        decision = evaluate_deployment_mode(StubResult(should_block=False), mode)
        assert decision.effective_should_block is False


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError):
        evaluate_deployment_mode(StubResult(), "not_a_mode")


def test_decision_serializes_to_dict():
    decision = evaluate_deployment_mode(StubResult(should_block=True), "shadow")
    data = decision.to_dict()
    assert data["mode"] == "shadow"
    assert data["original_should_block"] is True
    assert set(data) == {
        "mode",
        "original_should_block",
        "effective_should_block",
        "enforcement_suppressed",
        "warn_user",
        "reason",
    }
