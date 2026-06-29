"""Baseline detector registry.

Exposes the four transparent baseline detectors. No imports from any private
engine module; everything here is local, stdlib-only baseline logic.
"""

from __future__ import annotations

from .adversarial import detect_adversarial
from .clinical_intent import detect_clinical_intent
from .distress import DistressResult, detect_distress
from .output_review import OutputReviewResult, review_output
from .pii import PiiResult, detect_pii
from .policy import evaluate_policy

# DETECTORS is the original four-detector baseline registry (locked by tests).
# detect_adversarial and detect_clinical_intent are additive observation-only
# signals exposed via direct import / __all__, not part of this registry.
DETECTORS = {
    "pii": detect_pii,
    "distress": detect_distress,
    "policy": evaluate_policy,
    "output_review": review_output,
}

__all__ = [
    "detect_pii",
    "detect_distress",
    "evaluate_policy",
    "review_output",
    "detect_adversarial",
    "detect_clinical_intent",
    "PiiResult",
    "DistressResult",
    "OutputReviewResult",
    "DETECTORS",
]
