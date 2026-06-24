"""Axis 4 - live LLM-in-the-loop tests.

These hit a real provider (Anthropic or OpenAI) and are skipped by default. They
run only when ``SASKI_RUN_LIVE_TESTS=1`` and a provider key is present. The key
invariant they protect: the text actually sent to the provider is the redacted
``message_for_llm`` egress payload, never the raw user message with PII.

Run with:  SASKI_RUN_LIVE_TESTS=1 pytest -m live tests/harness/axis4_live.py
"""

from __future__ import annotations

import os

import pytest

from saski_shadow.analyzer import analyze_turn

pytestmark = pytest.mark.live

_PHI_MESSAGE = "My SSN is 123-45-6789. Briefly, what is a good way to keep data private?"


def _provider() -> str:
    return os.environ.get("SASKI_TEST_PROVIDER", "anthropic").strip().lower()


def _call_anthropic(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=os.environ.get("SASKI_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=os.environ.get("SASKI_OPENAI_MODEL", "gpt-4o-mini"),
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def _send(prompt: str) -> str:
    provider = _provider()
    if provider == "anthropic":
        return _call_anthropic(prompt)
    if provider == "openai":
        return _call_openai(prompt)
    pytest.skip(f"unknown SASKI_TEST_PROVIDER: {provider!r}")
    return ""


def test_live_redacted_payload_round_trips_through_provider(live_tests_enabled):
    if not live_tests_enabled:
        pytest.skip("live tests not enabled (set SASKI_RUN_LIVE_TESTS=1 and a key)")

    result = analyze_turn(_PHI_MESSAGE)
    # The egress payload must already be redacted before it ever leaves.
    assert result.message_for_llm is not None
    assert "123-45-6789" not in result.message_for_llm
    assert "[REDACTED_SSN]" in result.message_for_llm

    reply = _send(result.message_for_llm)
    assert isinstance(reply, str) and reply.strip()


def test_live_provider_never_receives_raw_pii(live_tests_enabled):
    if not live_tests_enabled:
        pytest.skip("live tests not enabled (set SASKI_RUN_LIVE_TESTS=1 and a key)")

    result = analyze_turn(_PHI_MESSAGE)
    sent = result.message_for_llm
    # Guard the redaction contract regardless of provider availability.
    assert sent is not None and "123-45-6789" not in sent
