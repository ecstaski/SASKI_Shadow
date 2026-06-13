"""Public enumerations for saski-shadow.

These enums define the integrator-facing vocabulary only. They do not
encode any safety-analysis logic.
"""

from __future__ import annotations

from enum import Enum


class DeploymentMode(str, Enum):
    ENFORCE = "enforce"
    SHADOW = "shadow"
    WARN = "warn"


class ModeTag(str, Enum):
    SASKI_ON = "saski_on"
    SASKI_OFF = "saski_off"
    SHADOW_MODE = "shadow_mode"
    WARN_MODE = "warn_mode"


class PublicOutcome(str, Enum):
    """Integrator-facing outcome vocabulary."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"
    CRISIS_REFERRAL = "crisis_referral"
    PHYSICAL_EMERGENCY_REFERRAL = "physical_emergency_referral"


class ExportActionLabel(str, Enum):
    """Research export taxonomy for turn payloads."""

    PASS_CLEAN = "PASS_CLEAN"
    BLOCK_SAFETY = "BLOCK_SAFETY"
    REWRITE_SENSITIVE = "REWRITE_SENSITIVE"
    PASS_WITH_MONITOR = "PASS_WITH_MONITOR"


class OutcomeStatus(str, Enum):
    RESOLVED = "Resolved"
    HARM = "Harm"
    UNKNOWN = "Unknown"
