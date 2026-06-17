"""Public US AI law starter set and a deterministic matcher.

This package holds law *facts only* — identifiers, jurisdictions, domains,
citations, effective dates, and plain-language notes. It contains no SASKI
enforcement mappings, thresholds, or internal policy logic. Matching is keyed
purely on integrator-supplied jurisdiction and domain.

The starter set is intentionally small and will expand as coverage grows.
"""

from __future__ import annotations

from .starter import STARTER_LAWS, match_laws

__all__ = ["STARTER_LAWS", "match_laws"]
