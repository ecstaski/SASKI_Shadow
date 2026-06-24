"""Adapters that convert analyzer results into downstream shapes."""

from __future__ import annotations

from .result_to_turn import result_to_jsonl_turn

__all__ = ["result_to_jsonl_turn"]
