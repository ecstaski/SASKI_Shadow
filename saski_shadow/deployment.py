"""Deployment gating.

Converts an engine's ``should_block`` signal into an integrator action
policy for shadow, warn, and enforce modes. This module makes no safety
decisions of its own; it only re-frames an already-computed signal.
"""

from __future__ import annotations

from .enums import DeploymentMode
from .types import AnalysisResult, DeploymentDecision

__all__ = ["DeploymentMode", "DeploymentDecision", "evaluate_deployment_mode"]


def _normalize_mode(mode: DeploymentMode | str) -> DeploymentMode:
    if isinstance(mode, DeploymentMode):
        return mode
    if isinstance(mode, str):
        try:
            return DeploymentMode(mode.strip().lower())
        except ValueError as exc:
            raise ValueError(f"Unknown deployment mode: {mode!r}") from exc
    raise TypeError(f"mode must be DeploymentMode or str, got {type(mode).__name__}")


def evaluate_deployment_mode(
    result: AnalysisResult,
    mode: DeploymentMode | str = DeploymentMode.ENFORCE,
) -> DeploymentDecision:
    """Convert engine should_block into integrator action policy for shadow/warn/enforce."""
    normalized = _normalize_mode(mode)
    original = bool(getattr(result, "should_block", False))

    if normalized is DeploymentMode.ENFORCE:
        return DeploymentDecision(
            mode=DeploymentMode.ENFORCE.value,
            original_should_block=original,
            effective_should_block=original,
            enforcement_suppressed=False,
            warn_user=False,
            reason="Enforce mode: block signal applied as the effective decision.",
        )

    if normalized is DeploymentMode.SHADOW:
        return DeploymentDecision(
            mode=DeploymentMode.SHADOW.value,
            original_should_block=original,
            effective_should_block=False,
            enforcement_suppressed=original,
            warn_user=False,
            reason="Shadow mode: block signal observed but not enforced.",
        )

    # DeploymentMode.WARN
    return DeploymentDecision(
        mode=DeploymentMode.WARN.value,
        original_should_block=original,
        effective_should_block=False,
        enforcement_suppressed=original,
        warn_user=original,
        reason="Warn mode: block signal surfaced to the user but not enforced.",
    )
