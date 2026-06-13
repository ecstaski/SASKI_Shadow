"""saski-shadow public API.

saski-shadow is a local baseline shadow observation package. It includes a
transparent baseline detection engine, validates and packages turn evidence,
and aggregates persisted turns into shadow pilot reports. It also accepts
compatible AnalysisResult objects from a licensed SASKI engine via the
optional integration adapter.
"""

from __future__ import annotations

from .aggregate.report import aggregate_shadow_report, load_turns_jsonl
from .deployment import DeploymentMode, evaluate_deployment_mode
from .enums import ExportActionLabel, ModeTag, OutcomeStatus, PublicOutcome
from .evidence import (
    build_evidence_bundle,
    generate_batch_manifest,
    record_research_event,
    turn_payload_from_result,
    update_bundle_outcome,
)
from .hashing import (
    CanonicalSerializationError,
    artifact_hash,
    canonical_bytes,
    canonical_dumps,
    compute_llm_payload_hash,
    compute_output_hash,
    hash_message,
    normalize_output_text_for_hashing,
    sha256_hex,
)
from .types import AnalysisResult, DeploymentDecision

__all__ = [
    "DeploymentMode",
    "DeploymentDecision",
    "evaluate_deployment_mode",
    "AnalysisResult",
    "PublicOutcome",
    "ExportActionLabel",
    "ModeTag",
    "OutcomeStatus",
    "CanonicalSerializationError",
    "canonical_dumps",
    "canonical_bytes",
    "sha256_hex",
    "hash_message",
    "normalize_output_text_for_hashing",
    "compute_output_hash",
    "compute_llm_payload_hash",
    "artifact_hash",
    "turn_payload_from_result",
    "build_evidence_bundle",
    "generate_batch_manifest",
    "record_research_event",
    "update_bundle_outcome",
    "aggregate_shadow_report",
    "load_turns_jsonl",
]
