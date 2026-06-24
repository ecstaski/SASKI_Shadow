"""Shared pytest configuration for saski-shadow.

Loads an optional repo-root ``.env`` (if ``python-dotenv`` and the file are
both available) and exposes fixtures for FULL_PIPELINE / live LLM testing.

Live tests hit external providers (Anthropic, OpenAI) and are skipped by
default. They run only when ``SASKI_RUN_LIVE_TESTS=1`` and at least one
provider API key is present. Mark such tests with ``@pytest.mark.live``.
"""

from __future__ import annotations

import os
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_ENV_PATH = _REPO_ROOT / ".env"


def _load_dotenv() -> None:
    """Load repo-root .env if python-dotenv and the file are both present.

    Fails gracefully: a missing package or missing file is a no-op so the
    normal (no-secrets) test run is unaffected.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    if _ENV_PATH.exists():
        load_dotenv(_ENV_PATH)


_load_dotenv()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: FULL_PIPELINE tests that call external LLM providers "
        "(skipped unless SASKI_RUN_LIVE_TESTS=1 and an API key is present).",
    )


@pytest.fixture
def anthropic_api_key() -> str | None:
    """Return ANTHROPIC_API_KEY from the environment, or None when unset."""
    return os.environ.get("ANTHROPIC_API_KEY")


@pytest.fixture
def openai_api_key() -> str | None:
    """Return OPENAI_API_KEY from the environment, or None when unset."""
    return os.environ.get("OPENAI_API_KEY")


@pytest.fixture
def live_tests_enabled() -> bool:
    """True only when live tests are opted in AND a provider key is present."""
    opted_in = os.environ.get("SASKI_RUN_LIVE_TESTS") == "1"
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    return opted_in and has_key
