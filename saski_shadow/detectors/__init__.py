"""Baseline detector registry.

Exposes the four transparent baseline detectors. No imports from any private
engine module; everything here is local, stdlib-only baseline logic.
"""

from __future__ import annotations

from .distress import DistressResult, detect_distress
from .output_review import OutputReviewResult, review_output
from .pii import PiiResult, detect_pii
from .policy import evaluate_policy

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
    "PiiResult",
    "DistressResult",
    "OutputReviewResult",
    "DETECTORS",
]
