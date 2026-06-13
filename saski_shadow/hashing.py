"""Deterministic canonical serialization and SHA-256 hashing helpers.

Standard library only. These helpers produce stable, reproducible hashes
so that turn evidence can be exported without any raw text.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Any

# Number of decimal places used to quantize floats before serialization so
# that equivalent values hash identically across platforms.
FLOAT_QUANTIZATION_DECIMALS = 8


class CanonicalSerializationError(Exception):
    """Raised when canonical serialization fails (e.g. NaN/Infinity)."""


def _quantize_float(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        raise CanonicalSerializationError("Non-finite float cannot be canonicalized")
    # Add 0.0 to normalize negative zero to positive zero.
    return round(value, FLOAT_QUANTIZATION_DECIMALS) + 0.0


def _to_canonical_value(obj: Any) -> Any:
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return _quantize_float(obj)
    if obj is None or isinstance(obj, (str, int)):
        return obj
    if isinstance(obj, dict):
        return {str(key): _to_canonical_value(val) for key, val in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_canonical_value(item) for item in obj]
    raise CanonicalSerializationError(
        f"Unsupported type for canonical serialization: {type(obj).__name__}"
    )


def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON string: sorted dict keys, stable float quantization."""
    canonical = _to_canonical_value(obj)
    try:
        return json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalSerializationError(str(exc)) from exc


def canonical_bytes(obj: Any) -> bytes:
    """UTF-8 bytes of canonical_dumps(obj)."""
    return canonical_dumps(obj).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """SHA-256 lowercase hex digest."""
    return hashlib.sha256(data).hexdigest()


def hash_message(text: str) -> str:
    """Input hash: NFKD-normalized, stripped text -> SHA-256 hex."""
    normalized = unicodedata.normalize("NFKD", text).strip()
    return sha256_hex(normalized.encode("utf-8"))


def normalize_output_text_for_hashing(text: str) -> str:
    """Strip leading/trailing whitespace; preserve case and internal spacing."""
    return text.strip()


def compute_output_hash(output_text: str) -> str:
    """SHA-256 of normalized output text."""
    return sha256_hex(normalize_output_text_for_hashing(output_text).encode("utf-8"))


def compute_llm_payload_hash(
    message_for_llm: str,
    history_for_llm: list[dict[str, Any]] | None = None,
    system_prompt_for_llm: str | None = None,
) -> str:
    """Canonical SHA-256 of governed LLM egress payload (hashes only in exports)."""
    payload = {
        "message_for_llm": message_for_llm,
        "history_for_llm": history_for_llm or [],
        "system_prompt_for_llm": system_prompt_for_llm,
    }
    return sha256_hex(canonical_bytes(payload))


def artifact_hash(payload: dict[str, Any]) -> str:
    """Stable 32-char hex prefix of canonical payload hash for transport audit chaining."""
    return sha256_hex(canonical_bytes(payload))[:32]
