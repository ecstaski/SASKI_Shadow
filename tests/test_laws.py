"""Tests for the starter law set and the jurisdiction/domain matcher."""

from saski_shadow.laws import STARTER_LAWS, match_laws


def test_starter_set_has_expected_count_and_fact_only_fields():
    assert len(STARTER_LAWS) == 14
    required = {"law_id", "jurisdiction", "domain", "citation", "effective_date", "note"}
    for law in STARTER_LAWS:
        assert set(law) == required


def test_exact_state_domain_match_names_specific_law():
    matched = match_laws("US-CA", "healthcare")
    ids = {law["law_id"] for law in matched}
    assert ids == {"US-CA-AB3030-HEALTH", "US-CA-HEALTH-ADVICE-AI"}


def test_domain_must_match_exactly():
    # CA has chatbot and healthcare laws, but no employment law in the set.
    assert match_laws("US-CA", "employment") == []


def test_nyc_turn_matches_both_city_and_state_laws():
    matched = match_laws("US-NY-NYC", "employment")
    ids = {law["law_id"] for law in matched}
    assert "US-NYC-AEDT" in ids  # city-specific


def test_state_only_turn_does_not_match_city_specific_law():
    # A plain US-NY employment turn must NOT pick up the NYC-only AEDT law.
    matched = match_laws("US-NY", "employment")
    ids = {law["law_id"] for law in matched}
    assert "US-NYC-AEDT" not in ids


def test_missing_jurisdiction_or_domain_returns_empty():
    assert match_laws(None, "healthcare") == []
    assert match_laws("US-CA", None) == []
    assert match_laws("", "") == []


def test_unknown_jurisdiction_returns_empty():
    assert match_laws("US-ZZ", "consumer_chatbot") == []


def test_match_returns_independent_copies():
    first = match_laws("US-NV", "mental_health")
    first[0]["note"] = "mutated"
    second = match_laws("US-NV", "mental_health")
    assert second[0]["note"] != "mutated"
