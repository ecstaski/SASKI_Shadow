"""Baseline analysis pipeline.

Runs an ordered, transparent baseline pipeline over a single user message and
returns an object compatible with the ``AnalysisResult`` protocol so it flows
through the existing evidence, deployment, and aggregation functions.

Stages run in this fixed order:
1. normalize_input
2. detect_pii
3. detect_distress
4. evaluate_policy
5. review_output
6. decide_outcome
7. sanitize_egress
8. build_evidence

No stage imports from any private engine module, and no stage encodes a
numeric decision threshold. Outcome and governance tier are assigned from
the public behavioral contracts only.
"""

from __future__ import annotations

import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from ..detectors import detect_distress, detect_pii, evaluate_policy, review_output
from ..enums import PublicOutcome
from ..hashing import (
    artifact_hash,
    canonical_bytes,
    compute_llm_payload_hash,
    compute_output_hash,
    hash_message,
    sha256_hex,
)

_DETECTOR_PROFILE = "baseline-v1"
_DEFAULT_POLICY_ID = "baseline-v1"
_VALID_ENFORCEMENT_MODES = {"enforce", "shadow", "warn"}
_VALID_JURISDICTION_SOURCES = {"integrator_supplied", "not_provided", "unknown"}


@dataclass
class BaselineAnalysisResult:
    """AnalysisResult-compatible result produced by the baseline analyzer."""

    should_block: bool
    action: str
    is_crisis: bool
    pii_detected: bool
    pii_types: list[str]
    envelope: dict[str, Any] | None
    policy_id: str | None
    policy_hash: str | None
    pipeline_ms: float
    processing_time_ms: float
    model_id: str | None
    provider_id: str | None
    metadata: dict[str, Any] | None

    def get_audit_record(self) -> dict[str, Any]:
        summary = (self.metadata or {}).get("engine_summary", {})
        return {
            "timestamp": (self.envelope or {}).get("timestamp_utc"),
            "outcome": summary.get("outcome"),
            "risk_band": summary.get("risk_band"),
            "pii_detected": self.pii_detected,
            "pii_types": list(self.pii_types),
        }


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_input(message: str) -> str:
    if not isinstance(message, str):
        return ""
    return unicodedata.normalize("NFKC", message).strip()


def _decide_outcome(
    policy_decisions: list[dict[str, Any]],
    escalation_detected: bool,
) -> tuple[PublicOutcome, bool]:
    # Block only when an integrator policy rule explicitly blocks. Distress
    # phrase matches never block on their own; they surface as a warning.
    actions = {str(d.get("action", "")).lower() for d in policy_decisions}

    if "block" in actions:
        return PublicOutcome.BLOCK, True
    if "human_review" in actions:
        return PublicOutcome.HUMAN_REVIEW, False
    if escalation_detected or "warn" in actions:
        return PublicOutcome.WARN, False
    return PublicOutcome.ALLOW, False


def _governance_tier(
    *,
    would_block: bool,
    escalation_detected: bool,
    outcome: PublicOutcome,
    pii_detected: bool,
) -> str:
    if (
        would_block
        or escalation_detected
        or outcome in (PublicOutcome.CRISIS_REFERRAL, PublicOutcome.PHYSICAL_EMERGENCY_REFERRAL)
    ):
        return "tier_escalation"
    if pii_detected or outcome is PublicOutcome.WARN:
        return "tier_warning"
    return "tier_clean"


def _risk_band(*, should_block: bool, tier: str) -> str:
    if should_block:
        return "critical"
    if tier == "tier_escalation":
        return "elevated"
    if tier == "tier_warning":
        return "moderate"
    return "low"


def _enforcement_mode(session_context: dict[str, Any]) -> str:
    mode = str(session_context.get("enforcement_mode", "shadow")).lower()
    return mode if mode in _VALID_ENFORCEMENT_MODES else "shadow"


def _jurisdiction_source(session_context: dict[str, Any]) -> str:
    supplied = session_context.get("jurisdiction_source")
    if isinstance(supplied, str) and supplied in _VALID_JURISDICTION_SOURCES:
        return supplied
    if session_context.get("user_jurisdiction"):
        return "integrator_supplied"
    return "not_provided"


def analyze_turn(
    message: str,
    session_context: dict | None = None,
    policy: dict | None = None,
) -> BaselineAnalysisResult:
    """Run the ordered public baseline pipeline on a single user message."""
    session_context = session_context or {}
    timings: dict[str, float] = {}
    started = perf_counter()

    # Stage 1: normalize_input
    t0 = perf_counter()
    normalized = _normalize_input(message)
    timings["normalize_input"] = (perf_counter() - t0) * 1000.0

    # Stage 2: detect_pii
    t0 = perf_counter()
    pii = detect_pii(normalized)
    timings["detect_pii"] = (perf_counter() - t0) * 1000.0

    # Stage 3: detect_distress
    t0 = perf_counter()
    distress = detect_distress(
        normalized, extra_indicators=session_context.get("extra_distress_indicators")
    )
    timings["detect_distress"] = (perf_counter() - t0) * 1000.0

    # Stage 4: evaluate_policy
    t0 = perf_counter()
    signals = {
        "text": normalized,
        "pii_detected": pii.redaction_applied,
        "pii_types": pii.pii_types,
        "escalation_detected": distress.escalation_detected,
    }
    policy_decisions = evaluate_policy(signals, policy)
    timings["evaluate_policy"] = (perf_counter() - t0) * 1000.0

    # Stage 5: review_output (only when an assistant output is supplied)
    t0 = perf_counter()
    assistant_output = session_context.get("assistant_output")
    if isinstance(assistant_output, str) and assistant_output:
        review = review_output(
            assistant_output,
            input_pii_types=pii.pii_types,
            policy=policy,
            extra_escalation_claims=session_context.get("extra_escalation_claims"),
        )
        output_review = {
            "pii_leaked_types": review.pii_leaked_types,
            "human_escalation_claimed": review.human_escalation_claimed,
            "policy_boundary_hits": review.policy_boundary_hits,
            "findings": review.findings,
        }
        output_hash = compute_output_hash(assistant_output)
    else:
        output_review = {"findings": []}
        output_hash = None
    timings["review_output"] = (perf_counter() - t0) * 1000.0

    # Stage 6: decide_outcome (contract 5.3 vocabulary, contract 5.5 tier)
    t0 = perf_counter()
    outcome, should_block = _decide_outcome(policy_decisions, distress.escalation_detected)
    would_block = should_block
    tier = _governance_tier(
        would_block=would_block,
        escalation_detected=distress.escalation_detected,
        outcome=outcome,
        pii_detected=pii.redaction_applied,
    )
    risk_band = _risk_band(should_block=should_block, tier=tier)
    timings["decide_outcome"] = (perf_counter() - t0) * 1000.0

    # Stage 7: sanitize_egress (redacted message with PII placeholders)
    t0 = perf_counter()
    redacted_message = pii.redacted_text
    message_for_llm_hash = compute_llm_payload_hash(redacted_message)
    timings["sanitize_egress"] = (perf_counter() - t0) * 1000.0

    # Stage 8: build_evidence (envelope + transport audit fields)
    t0 = perf_counter()
    run_id = f"run_{uuid.uuid4().hex}"
    timestamp_utc = _now_utc_iso()
    input_hash = hash_message(message if isinstance(message, str) else "")
    policy_id = (policy or {}).get("policy_id") or _DEFAULT_POLICY_ID
    policy_hash = sha256_hex(canonical_bytes(policy)) if policy else None

    envelope = {
        "envelope_version": "1.0",
        "run_id": run_id,
        "policy_id": policy_id,
        "policy_hash": policy_hash,
        "timestamp_utc": timestamp_utc,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "integrator_signature": None,
        "events": [],
        "invariant_summary": {},
    }

    transport_record = {
        "record_version": "1.0",
        "run_id": run_id,
        "enforcement_mode": _enforcement_mode(session_context),
        "jurisdiction_source": _jurisdiction_source(session_context),
        "pii_detected": pii.redaction_applied,
        "pii_types": pii.pii_types,
        "redaction_applied": pii.redaction_applied,
        "message_for_llm_hash": message_for_llm_hash,
        "prev_artifact_hash": session_context.get("prev_artifact_hash"),
        "violation_events": [],
    }
    transport_record["artifact_hash"] = artifact_hash(transport_record)
    timings["build_evidence"] = (perf_counter() - t0) * 1000.0

    total_ms = (perf_counter() - started) * 1000.0

    # Factual passthrough of integrator-supplied compliance context. These are
    # not analyzed or interpreted here; they exist so the aggregator can match
    # public laws by jurisdiction and domain downstream.
    user_jurisdiction = session_context.get("user_jurisdiction")
    domain = session_context.get("domain")

    engine_summary = {
        "outcome": outcome.value,
        "risk_band": risk_band,
        "pii_detected": pii.redaction_applied,
        "pii_types": pii.pii_types,
        "escalation_detected": distress.escalation_detected,
        "would_block": would_block,
        "governance_tier": tier,
        "phase_timings": timings,
        "user_jurisdiction": str(user_jurisdiction) if user_jurisdiction else None,
        "domain": str(domain) if domain else None,
    }

    metadata = {
        "engine_summary": engine_summary,
        "transport_audit_record": transport_record,
        "detector_profile": _DETECTOR_PROFILE,
        "compliance_decisions": policy_decisions,
        "output_review": output_review,
    }

    return BaselineAnalysisResult(
        should_block=should_block,
        action=outcome.value,
        is_crisis=False,
        pii_detected=pii.redaction_applied,
        pii_types=pii.pii_types,
        envelope=envelope,
        policy_id=policy_id,
        policy_hash=policy_hash,
        pipeline_ms=total_ms,
        processing_time_ms=total_ms,
        model_id=None,
        provider_id=None,
        metadata=metadata,
    )
