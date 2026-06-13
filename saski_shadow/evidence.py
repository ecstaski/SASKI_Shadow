"""Turn evidence serialization, session bundles, and export boundaries.

This module turns ``AnalysisResult`` objects into hash-only turn payloads,
assembles them into integrity-checked session bundles, and enforces a strict
export boundary that rejects raw text. It performs no safety analysis: all
signals are read from the result the integrator supplies.
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Iterable

from .enums import ExportActionLabel, ModeTag, OutcomeStatus, PublicOutcome
from .hashing import canonical_bytes, compute_output_hash, hash_message, sha256_hex
from .types import AnalysisResult

# Keys rejected in strict export boundary (no raw text may cross the boundary).
RAW_TEXT_KEYS: frozenset[str] = frozenset(
    {
        "raw_prompt",
        "raw_response",
        "message_for_llm",
        "history_for_llm",
        "system_prompt_for_llm",
        "prompt",
        "completion",
    }
)

# Required per-turn keys when strict_export_boundary is enabled.
_REQUIRED_STRICT_KEYS = (
    "run_id",
    "session_id",
    "policy_hash",
    "input_hash",
    "output_hash",
    "mode_tag",
    "timestamp_ms",
    "action_label",
)

# Keys whose value may be null while still satisfying the strict boundary.
_NULLABLE_STRICT_KEYS = frozenset({"output_hash", "policy_hash"})

_MODE_TAG_VALUES = frozenset(tag.value for tag in ModeTag)
_ACTION_LABEL_VALUES = frozenset(label.value for label in ExportActionLabel)
_OUTCOME_STATUS_VALUES = frozenset(status.value for status in OutcomeStatus)

# Opaque engine action tokens mapped to public outcome vocabulary.
_OUTCOME_MAP = {
    "continue": PublicOutcome.ALLOW,
    "empathy": PublicOutcome.ALLOW,
    "allow": PublicOutcome.ALLOW,
    "monitor": PublicOutcome.WARN,
    "resources": PublicOutcome.WARN,
    "warn": PublicOutcome.WARN,
    "block": PublicOutcome.BLOCK,
    "human_review": PublicOutcome.HUMAN_REVIEW,
    "crisis_referral": PublicOutcome.CRISIS_REFERRAL,
    "physical_emergency_referral": PublicOutcome.PHYSICAL_EMERGENCY_REFERRAL,
}

_MONITORING_TOKENS = frozenset({"monitor", "resources", "warn"})


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_epoch_ms(timestamp_utc: str | None, timestamp_ms: int | None = None) -> int:
    if timestamp_ms is not None:
        return int(timestamp_ms)
    if timestamp_utc:
        try:
            parsed = datetime.fromisoformat(timestamp_utc.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
        except ValueError:
            pass
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _normalize_action_token(action: Any) -> str:
    if action is None:
        return ""
    value = getattr(action, "value", action)
    return str(value).strip().lower()


def _extract_envelope_field(result: AnalysisResult, key: str) -> Any:
    envelope = getattr(result, "envelope", None)
    if isinstance(envelope, dict):
        return envelope.get(key)
    return None


def _resolve_output_hash(
    output_hash: str | None,
    llm_response_text: str | None,
    envelope: dict[str, Any],
) -> str | None:
    if output_hash:
        return output_hash
    if llm_response_text is not None:
        return compute_output_hash(llm_response_text)
    if isinstance(envelope, dict):
        return envelope.get("output_hash")
    return None


def _resolve_latency(result: AnalysisResult) -> float:
    for attr in ("pipeline_ms", "processing_time_ms"):
        value = getattr(result, attr, None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return 0.0


def map_public_outcome(result: AnalysisResult) -> PublicOutcome:
    """Map engine action + flags to approved public outcome vocabulary."""
    token = _normalize_action_token(getattr(result, "action", None))
    if token in _OUTCOME_MAP:
        return _OUTCOME_MAP[token]
    if bool(getattr(result, "should_block", False)):
        return PublicOutcome.BLOCK
    return PublicOutcome.ALLOW


def _is_monitoring_action(result: AnalysisResult) -> bool:
    return _normalize_action_token(getattr(result, "action", None)) in _MONITORING_TOKENS


def _sanitization_detected(result: AnalysisResult) -> bool:
    # Uses only pii_detected plus optional generic metadata length hints.
    if not bool(getattr(result, "pii_detected", False)):
        return False
    metadata = getattr(result, "metadata", None) or {}
    redacted_len = metadata.get("redacted_length")
    egress_len = metadata.get("egress_length")
    if isinstance(redacted_len, (int, float)) and isinstance(egress_len, (int, float)):
        return redacted_len != egress_len
    return True


def infer_export_action_label(result: AnalysisResult) -> str:
    """Map engine signals to ExportActionLabel without exposing engine internals."""
    if bool(getattr(result, "should_block", False)):
        return ExportActionLabel.BLOCK_SAFETY.value
    if _is_monitoring_action(result):
        return ExportActionLabel.PASS_WITH_MONITOR.value
    if _sanitization_detected(result):
        return ExportActionLabel.REWRITE_SENSITIVE.value
    return ExportActionLabel.PASS_CLEAN.value


def _validate_mode_tag(mode_tag: str) -> None:
    if mode_tag not in _MODE_TAG_VALUES:
        raise ValueError(f"Invalid mode_tag: {mode_tag!r}")


def _validate_action_label(action_label: str) -> None:
    if action_label not in _ACTION_LABEL_VALUES:
        raise ValueError(f"Invalid action_label: {action_label!r}")


def _validate_outcome_status(status: str) -> None:
    if status not in _OUTCOME_STATUS_VALUES:
        raise ValueError(f"Invalid outcome status: {status!r}")


def _build_engine_summary(result: AnalysisResult) -> dict[str, Any]:
    # Slim audit passthrough: outcome, risk_band, pii_detected only.
    risk_band = None
    record = getattr(result, "get_audit_record", None)
    if callable(record):
        try:
            raw = record()
        except Exception:
            raw = None
        if isinstance(raw, dict):
            risk_band = raw.get("risk_band")
    return {
        "outcome": map_public_outcome(result).value,
        "risk_band": risk_band,
        "pii_detected": bool(getattr(result, "pii_detected", False)),
    }


def turn_payload_from_result(
    result: AnalysisResult,
    *,
    turn_index: int,
    session_id: str,
    timestamp_utc: str | None = None,
    model_id: str | None = None,
    provider_id: str | None = None,
    response_hash: str | None = None,
    output_hash: str | None = None,
    llm_response_text: str | None = None,
    correlation_id: str | None = None,
    mode_tag: str = "saski_on",
    action_label: str | None = None,
    outcome_linkage: dict[str, Any] | None = None,
    timestamp_ms: int | None = None,
) -> dict[str, Any]:
    """Build one hash-only turn dict from an AnalysisResult."""
    _validate_mode_tag(mode_tag)
    timestamp = timestamp_utc or _now_utc_iso()

    envelope = getattr(result, "envelope", None)
    envelope = envelope if isinstance(envelope, dict) else {}

    metadata = getattr(result, "metadata", None) or {}
    transport_audit_record = metadata.get("transport_audit_record")

    resolved_output_hash = _resolve_output_hash(output_hash, llm_response_text, envelope)
    label = action_label if action_label is not None else infer_export_action_label(result)
    _validate_action_label(label)

    run_id = (
        _extract_envelope_field(result, "run_id")
        or correlation_id
        or f"{session_id}-{turn_index}"
    )

    payload: dict[str, Any] = {
        "turn_index": int(turn_index),
        "timestamp_utc": timestamp,
        "timestamp_ms": _to_epoch_ms(timestamp, timestamp_ms),
        "session_id": session_id,
        "run_id": run_id,
        "policy_id": getattr(result, "policy_id", None),
        "policy_hash": getattr(result, "policy_hash", None),
        "input_hash": _extract_envelope_field(result, "input_hash"),
        "output_hash": resolved_output_hash,
        "response_hash": response_hash,
        "mode_tag": mode_tag,
        "action_label": label,
        "latency_ms": _resolve_latency(result),
        "model_id": model_id if model_id is not None else getattr(result, "model_id", None),
        "provider_id": (
            provider_id if provider_id is not None else getattr(result, "provider_id", None)
        ),
        "correlation_id": correlation_id,
        "outcome_linkage": outcome_linkage,
        "envelope": envelope,
        "engine_summary": _build_engine_summary(result),
    }

    if isinstance(transport_audit_record, dict):
        payload["transport_audit_record"] = transport_audit_record

    return payload


def _ordered_turns(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        turns,
        key=lambda turn: (turn.get("turn_index", 0), turn.get("timestamp_ms", 0)),
    )


def _reject_raw_text_keys(obj: Any) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in RAW_TEXT_KEYS:
                raise ValueError(f"Strict export boundary: raw text key not allowed: {key!r}")
            _reject_raw_text_keys(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            _reject_raw_text_keys(item)


def _enforce_strict_boundary(turn: dict[str, Any]) -> None:
    _reject_raw_text_keys(turn)
    missing: list[str] = []
    for key in _REQUIRED_STRICT_KEYS:
        if key not in turn:
            missing.append(key)
        elif key not in _NULLABLE_STRICT_KEYS and turn[key] in (None, ""):
            missing.append(key)
    if missing:
        raise ValueError(
            f"Strict export boundary: missing or empty required keys: {sorted(missing)}"
        )


def _canonical_turns_for_checksum(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return list(turns)


def build_evidence_bundle(
    session_id: str,
    turns: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    *,
    strict_export_boundary: bool = False,
) -> dict[str, Any]:
    """Ordered session bundle with integrity_checksum."""
    ordered = _ordered_turns(turns)
    if strict_export_boundary:
        for turn in ordered:
            _enforce_strict_boundary(turn)

    checksum_basis = _canonical_turns_for_checksum(ordered)
    integrity_checksum = sha256_hex(canonical_bytes(checksum_basis))

    return {
        "session_id": session_id,
        "turn_count": len(ordered),
        "turns": ordered,
        "metadata": metadata or {},
        "strict_export_boundary": strict_export_boundary,
        "integrity_checksum": integrity_checksum,
        "generated_at_utc": _now_utc_iso(),
    }


def generate_batch_manifest(
    jsonl_paths: Iterable[str],
    manifest_path: str | None = None,
) -> dict[str, Any]:
    """Per-file and batch-root SHA-256 manifest."""
    files: list[dict[str, Any]] = []
    for path in jsonl_paths:
        data = pathlib.Path(path).read_bytes()
        files.append(
            {
                "path": str(path),
                "sha256": sha256_hex(data),
                "size_bytes": len(data),
            }
        )
    files.sort(key=lambda entry: entry["path"])
    batch_root_hash = sha256_hex(canonical_bytes([entry["sha256"] for entry in files]))

    manifest = {
        "manifest_version": "1.0",
        "generated_at_utc": _now_utc_iso(),
        "file_count": len(files),
        "files": files,
        "batch_root_hash": batch_root_hash,
    }

    if manifest_path:
        pathlib.Path(manifest_path).write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )

    return manifest


def record_research_event(
    input_text: str,
    output_text: str,
    mode_tag: str,
    session_id: str,
) -> dict[str, Any]:
    """One-turn strict-boundary bundle without raw text."""
    _validate_mode_tag(mode_tag)
    timestamp = _now_utc_iso()
    turn = {
        "turn_index": 0,
        "timestamp_utc": timestamp,
        "timestamp_ms": _to_epoch_ms(timestamp),
        "session_id": session_id,
        "run_id": f"{session_id}-0",
        "policy_hash": None,
        "input_hash": hash_message(input_text),
        "output_hash": compute_output_hash(output_text),
        "mode_tag": mode_tag,
        "action_label": ExportActionLabel.PASS_CLEAN.value,
    }
    return build_evidence_bundle(session_id, [turn], strict_export_boundary=True)


def update_bundle_outcome(
    run_id: str,
    status: str,
    corrective_action_taken: bool,
    latency_ms: float | None = None,
) -> dict[str, Any]:
    """Async outcome update payload keyed by run_id."""
    _validate_outcome_status(status)
    payload: dict[str, Any] = {
        "run_id": run_id,
        "status": status,
        "corrective_action_taken": bool(corrective_action_taken),
        "updated_at_utc": _now_utc_iso(),
    }
    if latency_ms is not None:
        payload["latency_ms"] = float(latency_ms)
    return payload
