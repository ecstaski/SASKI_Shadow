"""Optional adapter for the licensed SASKI engine.

This module is an optional extra. It maps a licensed engine result onto the
``AnalysisResult`` protocol so it can flow through the same evidence,
deployment, and aggregation functions as the local baseline analyzer.

It is intentionally NOT imported by ``saski_shadow.__init__`` or by any core
module. Import it explicitly:

    from saski_shadow.integrations.saski_sdk import adapt_engine_result

The adapter reads engine results by duck typing and does not import any
private engine package. Only a strict allowlist of normalized fields is
copied into the turn ``engine_summary``. No scores, tags, obfuscation
signals, crisis text, raw message text, routing decisions, threshold values,
or internal module names are ever read or forwarded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..enums import PublicOutcome
from ..evidence import map_public_outcome, turn_payload_from_result

# Only these fields may appear in the engine_summary block.
_ALLOWED_RISK_BANDS = {"low", "moderate", "elevated", "critical"}
_ALLOWED_TIERS = {"tier_clean", "tier_warning", "tier_escalation"}
_PUBLIC_OUTCOMES = {o.value for o in PublicOutcome}

# Public schema field allowlists for opaque passthrough blocks.
_ENVELOPE_FIELDS = (
    "envelope_version",
    "run_id",
    "policy_id",
    "policy_hash",
    "timestamp_utc",
    "input_hash",
    "output_hash",
    "integrator_signature",
    "events",
    "invariant_summary",
)
_TRANSPORT_FIELDS = (
    "record_version",
    "run_id",
    "enforcement_mode",
    "jurisdiction_source",
    "pii_detected",
    "pii_types",
    "redaction_applied",
    "message_for_llm_hash",
    "artifact_hash",
    "prev_artifact_hash",
    "violation_events",
)


@dataclass
class AdaptedEngineResult:
    """AnalysisResult-compatible view over an allowlisted engine result."""

    should_block: bool
    action: str
    is_crisis: bool
    pii_detected: bool
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
            "outcome": summary.get("outcome"),
            "risk_band": summary.get("risk_band"),
            "pii_detected": summary.get("pii_detected"),
            "pii_types": list(summary.get("pii_types", [])),
        }


def _coerce_outcome(result: Any) -> str:
    candidate = getattr(result, "outcome", None)
    value = getattr(candidate, "value", candidate)
    if isinstance(value, str) and value in _PUBLIC_OUTCOMES:
        return value
    return map_public_outcome(result).value


def _coerce_risk_band(value: Any) -> str | None:
    return value if value in _ALLOWED_RISK_BANDS else None


def _coerce_tier(value: Any) -> str:
    return value if value in _ALLOWED_TIERS else "tier_clean"


def _coerce_pii_types(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return []


def _coerce_phase_timings(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    timings: dict[str, float] = {}
    for key, val in value.items():
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            timings[str(key)] = float(val)
    return timings


def _filter_dict(source: Any, allowed: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(source, dict):
        return {}
    return {key: source[key] for key in allowed if key in source}


def _engine_metadata(result: Any) -> dict[str, Any]:
    metadata = getattr(result, "metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def adapt_engine_result(result: Any) -> AdaptedEngineResult:
    """Wrap a licensed engine result as AnalysisResult (optional extra only)."""
    metadata = _engine_metadata(result)
    source_summary = metadata.get("engine_summary")
    source_summary = source_summary if isinstance(source_summary, dict) else {}

    outcome = _coerce_outcome(result)

    would_block = bool(
        source_summary.get("would_block", getattr(result, "should_block", False))
    )
    pii_detected = bool(source_summary.get("pii_detected", getattr(result, "pii_detected", False)))
    pii_types = _coerce_pii_types(source_summary.get("pii_types"))
    escalation_detected = bool(source_summary.get("escalation_detected", False))
    risk_band = _coerce_risk_band(source_summary.get("risk_band"))
    governance_tier = _coerce_tier(source_summary.get("governance_tier"))
    phase_timings = _coerce_phase_timings(source_summary.get("phase_timings"))

    engine_summary = {
        "outcome": outcome,
        "risk_band": risk_band,
        "pii_detected": pii_detected,
        "pii_types": pii_types,
        "escalation_detected": escalation_detected,
        "would_block": would_block,
        "governance_tier": governance_tier,
        "phase_timings": phase_timings,
    }

    adapted_metadata: dict[str, Any] = {"engine_summary": engine_summary}
    transport = _filter_dict(metadata.get("transport_audit_record"), _TRANSPORT_FIELDS)
    if transport:
        adapted_metadata["transport_audit_record"] = transport

    envelope = _filter_dict(getattr(result, "envelope", None), _ENVELOPE_FIELDS) or None

    return AdaptedEngineResult(
        should_block=would_block,
        action=outcome,
        is_crisis=bool(getattr(result, "is_crisis", False)),
        pii_detected=pii_detected,
        envelope=envelope,
        policy_id=getattr(result, "policy_id", None),
        policy_hash=getattr(result, "policy_hash", None),
        pipeline_ms=float(getattr(result, "pipeline_ms", 0.0) or 0.0),
        processing_time_ms=float(getattr(result, "processing_time_ms", 0.0) or 0.0),
        model_id=None,
        provider_id=None,
        metadata=adapted_metadata,
    )


def turn_payload_from_engine(result: Any, **kwargs: Any) -> dict[str, Any]:
    """Convenience: adapt + turn_payload_from_result in one call."""
    adapted = adapt_engine_result(result)
    payload = turn_payload_from_result(adapted, **kwargs)
    # Attach the full allowlisted engine_summary at persistence time so the
    # aggregator has tier, escalation, and phase timing fields.
    payload["engine_summary"] = dict((adapted.metadata or {}).get("engine_summary", {}))
    transport = (adapted.metadata or {}).get("transport_audit_record")
    if isinstance(transport, dict) and transport:
        payload["transport_audit_record"] = transport
    return payload
