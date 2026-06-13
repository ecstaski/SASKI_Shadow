"""Tests for canonical serialization and hashing helpers."""

import pytest

from saski_shadow import (
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


def test_canonical_dumps_sorts_keys_deterministically():
    assert canonical_dumps({"beta": 1, "alpha": 2}) == '{"alpha":2,"beta":1}'


def test_canonical_dumps_is_stable_across_calls():
    payload = {"two": [3, 2, 1], "one": {"y": 1, "x": 2}}
    assert canonical_dumps(payload) == canonical_dumps(dict(payload))


def test_canonical_bytes_is_utf8_encoding_of_dumps():
    payload = {"alpha": "beta"}
    assert canonical_bytes(payload) == canonical_dumps(payload).encode("utf-8")


def test_sha256_hex_is_lowercase_hex_of_fixed_length():
    digest = sha256_hex(b"alpha")
    assert len(digest) == 64
    assert digest == digest.lower()


def test_hash_message_ignores_surrounding_whitespace():
    assert hash_message("  alpha beta  ") == hash_message("alpha beta")


def test_normalize_output_preserves_internal_spacing():
    assert normalize_output_text_for_hashing("  alpha  beta  ") == "alpha  beta"


def test_compute_output_hash_matches_normalized_text():
    assert compute_output_hash("  alpha  ") == compute_output_hash("alpha")


def test_compute_llm_payload_hash_is_deterministic():
    first = compute_llm_payload_hash("alpha", history_for_llm=[{"role": "x"}], system_prompt_for_llm="beta")
    second = compute_llm_payload_hash("alpha", history_for_llm=[{"role": "x"}], system_prompt_for_llm="beta")
    assert first == second
    assert len(first) == 64


def test_artifact_hash_is_truncated_prefix():
    digest = artifact_hash({"alpha": "beta"})
    assert len(digest) == 32
    assert digest == sha256_hex(canonical_bytes({"alpha": "beta"}))[:32]


def test_non_finite_float_raises_canonical_error():
    with pytest.raises(CanonicalSerializationError):
        canonical_dumps({"value": float("nan")})


def test_unsupported_type_raises_canonical_error():
    with pytest.raises(CanonicalSerializationError):
        canonical_dumps({"value": {1, 2, 3}})
