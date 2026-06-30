"""Tests for the starter law set and the jurisdiction/domain matcher."""

import pathlib
from unittest.mock import patch

from saski_shadow.laws import STARTER_LAWS, coverage_summary, match_laws

README = pathlib.Path(__file__).resolve().parents[1] / "README.md"


def test_readme_law_coverage_counts_match_starter_set():
    """Guard: the README's Law Coverage figures must match the live data.

    If the starter set grows but the README is not updated, this fails.
    """
    text = README.read_text(encoding="utf-8")
    cov = coverage_summary()

    total = f"{cov['total_laws']} laws across {cov['total_states']}"
    assert total in text, f"README missing total-coverage figure: {total!r}"

    for domain, stats in cov["by_domain"].items():
        token = f"{stats['laws']} laws / {stats['states']} states"
        assert token in text, f"README missing {domain} figure: {token!r}"


def test_starter_set_has_expected_count_and_fact_only_fields():
    assert len(STARTER_LAWS) == 74
    required = {
        "law_id",
        "jurisdiction",
        "domains",
        "citation",
        "effective_date",
        "date_added",
        "note",
    }
    for law in STARTER_LAWS:
        assert set(law) == required
        assert isinstance(law["domains"], list)
        assert law["domains"]


def test_law_ids_are_unique():
    ids = [law["law_id"] for law in STARTER_LAWS]
    assert len(ids) == len(set(ids))


def test_exact_state_domain_match_names_specific_law():
    # A CA healthcare turn matches the two CA-specific laws plus every federal
    # ("US") healthcare law, since "US" is a broader prefix of "US-CA".
    matched = match_laws("US-CA", "healthcare")
    ids = {law["law_id"] for law in matched}
    assert ids == {
        "US-CA-AB3030-HEALTH",
        "US-CA-HEALTH-ADVICE-AI",
        "US-HIPAA",
        "US-FTC-HBNR",
        "US-42-CFR-PART-2",
        "US-ACA-1557",
    }


def test_domain_must_match_exactly():
    # CA mental_health turns surface multi-domain CA laws whose ``domains`` include
    # ``mental_health`` (no duplicate -MH law entries after registry migration).
    matched = match_laws("US-CA", "mental_health")
    ids = {law["law_id"] for law in matched}
    assert ids == {
        "US-CA-AB3030-HEALTH",
        "US-CA-COMPANION-CHATBOT",
        "US-CA-HEALTH-ADVICE-AI",
        "US-42-CFR-PART-2",
    }


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
    # A non-US jurisdiction matches nothing — the starter set is US-only, and
    # no law's jurisdiction is a prefix of "GB".
    assert match_laws("GB", "consumer_chatbot") == []


def test_federal_law_matches_any_us_subjurisdiction():
    # Federal ("US") laws apply to every US-prefixed turn in their domain,
    # including a US sub-jurisdiction with no state-specific law of its own.
    ids = {law["law_id"] for law in match_laws("US-ZZ", "consumer_chatbot")}
    assert "US-FTC-ACT-5" in ids
    assert "US-COPPA" in ids


def test_match_returns_independent_copies():
    first = match_laws("US-NV", "mental_health")
    first[0]["note"] = "mutated"
    second = match_laws("US-NV", "mental_health")
    assert second[0]["note"] != "mutated"


def test_single_string_domain_still_works():
    # Backward compatibility: a single domain string behaves as before.
    matched = match_laws("US", "csam")
    assert matched
    assert all("csam" in law["matched_domains"] for law in matched)


def test_list_of_domains_returns_laws_from_each_domain():
    matched = match_laws("US", ["consumer_chatbot", "csam"])
    matched_domains = {d for law in matched for d in law["matched_domains"]}
    assert "consumer_chatbot" in matched_domains
    assert "csam" in matched_domains


def test_child_turn_surfaces_both_coppa_and_a_csam_statute():
    # Core child-facing coverage: a US child turn spanning both domains must
    # surface COPPA (consumer_chatbot) and at least one CSAM statute (csam).
    matched = match_laws("US", ["consumer_chatbot", "csam"])
    ids = {law["law_id"] for law in matched}
    assert "US-COPPA" in ids
    assert any("csam" in law["matched_domains"] for law in matched)


def test_multi_domain_results_have_no_duplicate_law_ids():
    matched = match_laws("US", ["consumer_chatbot", "csam", "consumer_chatbot"])
    ids = [law["law_id"] for law in matched]
    assert len(ids) == len(set(ids))


def test_matched_law_includes_domains_and_matched_domains_fields():
    matched = match_laws("US-NV", "mental_health")
    assert matched
    law = matched[0]
    assert isinstance(law["domains"], list)
    assert law["domains"]
    assert law["matched_domains"] == ["mental_health"]
    assert law["domain"] == "mental_health"


def test_intersection_matching_multi_domain_law_entry():
    multi = {
        "law_id": "TEST-MULTI-DOMAIN-LAW",
        "jurisdiction": "US-NY",
        "domains": ["consumer_chatbot", "mental_health"],
        "citation": "Test citation",
        "effective_date": "2025-01-01",
        "date_added": "2026-01-01",
        "note": "Synthetic multi-domain entry for intersection coverage.",
    }
    with patch(
        "saski_shadow.laws.starter.STARTER_LAWS",
        STARTER_LAWS + (multi,),
    ):
        matched = match_laws("US-NY", "mental_health")
    by_id = {law["law_id"]: law for law in matched}
    assert "TEST-MULTI-DOMAIN-LAW" in by_id
    assert by_id["TEST-MULTI-DOMAIN-LAW"]["matched_domains"] == ["mental_health"]
    assert by_id["TEST-MULTI-DOMAIN-LAW"]["domains"] == [
        "consumer_chatbot",
        "mental_health",
    ]
