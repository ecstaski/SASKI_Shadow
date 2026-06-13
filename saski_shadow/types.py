"""Type definitions for saski-shadow.

Defines the duck-typed ``AnalysisResult`` protocol that any compatible
safety engine result may satisfy, plus the immutable deployment decision
record. No engine-specific result classes are referenced here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AnalysisResult(Protocol):
    """Duck-typed interface for objects produced by a safety engine."""

    should_block: bool
    action: Any  # engine-specific; mapped internally to PublicOutcome / ExportActionLabel
    is_crisis: bool
    pii_detected: bool
    envelope: Any | None
    policy_id: str | None
    policy_hash: str | None
    pipeline_ms: float
    processing_time_ms: float
    model_id: str | None
    provider_id: str | None
    metadata: dict[str, Any] | None

    def get_audit_record(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DeploymentDecision:
    mode: str
    original_should_block: bool
    effective_should_block: bool
    enforcement_suppressed: bool
    warn_user: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "original_should_block": self.original_should_block,
            "effective_should_block": self.effective_should_block,
            "enforcement_suppressed": self.enforcement_suppressed,
            "warn_user": self.warn_user,
            "reason": self.reason,
        }
