"""Tests for the conftest.py environment/key fixtures.

These verify the fixtures degrade gracefully when no keys are configured, which
is the normal (no-secrets) CI state. ``request.getfixturevalue`` is used so the
environment is cleared before the fixtures read it, regardless of fixture
instantiation order or a developer's local ``.env``.
"""

from __future__ import annotations


def test_api_key_fixtures_return_none_when_absent(monkeypatch, request):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert request.getfixturevalue("anthropic_api_key") is None
    assert request.getfixturevalue("openai_api_key") is None


def test_live_tests_disabled_when_env_absent(monkeypatch, request):
    monkeypatch.delenv("SASKI_RUN_LIVE_TESTS", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert request.getfixturevalue("live_tests_enabled") is False


def test_live_tests_disabled_when_opted_in_but_no_key(monkeypatch, request):
    # Opt-in alone is not enough; at least one key must be present.
    monkeypatch.setenv("SASKI_RUN_LIVE_TESTS", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert request.getfixturevalue("live_tests_enabled") is False
