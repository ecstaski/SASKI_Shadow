"""Axis 1 - law matching golden tables.

Deterministic, data-driven coverage of the matcher across all jurisdictions and
domains in ``STARTER_LAWS``. Covers the systematic gaps that involve law
matching: jurisdiction coverage (gap 1), federal-only turns (gap 4),
cross-domain isolation (gap 5), and future-effective bucketing (gap 6).

All expectations are derived from the live starter law set, never hardcoded, so
these tests stay correct as the set grows.
"""

from __future__ import annotations

from saski_shadow.aggregate.report import _split_laws_by_effective_date, _today_utc
from saski_shadow.laws import STARTER_LAWS, coverage_summary, match_laws
from saski_shadow.laws.starter import _law_domains

# Derived golden tables (single source of truth: STARTER_LAWS).
_PAIRS = sorted(
    {
        (law["jurisdiction"], domain)
        for law in STARTER_LAWS
        for domain in _law_domains(law)
    }
)
_DISTINCT_JURISDICTIONS = sorted({law["jurisdiction"] for law in STARTER_LAWS})
_FEDERAL_DOMAINS = {
    domain
    for law in STARTER_LAWS
    if law["jurisdiction"] == "US"
    for domain in _law_domains(law)
}
_ALL_DOMAINS = sorted({domain for law in STARTER_LAWS for domain in _law_domains(law)})


# --- Gap 1: jurisdiction coverage (all 36 jurisdictions) --------------------


def test_state_level_jurisdiction_count_is_36():
    # Locks the documented "36 jurisdictions" coverage figure.
    assert coverage_summary()["total_states"] == 36


def test_every_jurisdiction_domain_pair_returns_at_least_one_law():
    gaps = [(j, d) for (j, d) in _PAIRS if not match_laws(j, d)]
    assert gaps == [], f"jurisdiction/domain pairs with zero matches: {gaps}"


def test_every_distinct_jurisdiction_has_some_coverage():
    # Every jurisdiction present in the starter set must match in at least one of
    # its own domains. Reported as a list so genuine coverage gaps are visible.
    uncovered = []
    for jur in _DISTINCT_JURISDICTIONS:
        domains = {
            domain
            for law in STARTER_LAWS
            if law["jurisdiction"] == jur
            for domain in _law_domains(law)
        }
        if not any(match_laws(jur, d) for d in domains):
            uncovered.append(jur)
    assert uncovered == [], f"jurisdictions with zero coverage: {uncovered}"


def test_state_turns_surface_applicable_federal_laws():
    # Any US-XX jurisdiction must also surface the federal ("US") laws for any
    # domain that has federal entries.
    for jur, domain in _PAIRS:
        if jur == "US" or domain not in _FEDERAL_DOMAINS:
            continue
        matched = match_laws(jur, domain)
        assert any(
            law["jurisdiction"] == "US" for law in matched
        ), f"{jur}/{domain} did not surface a federal law"


# --- Gap 4: federal-only turns ----------------------------------------------


def test_federal_healthcare_turn_surfaces_federal_laws():
    matched = match_laws("US", "healthcare")
    ids = {law["law_id"] for law in matched}
    assert "US-HIPAA" in ids
    assert all(law["jurisdiction"] == "US" for law in matched)


def test_federal_consumer_chatbot_turn_surfaces_federal_laws():
    matched = match_laws("US", "consumer_chatbot")
    ids = {law["law_id"] for law in matched}
    assert "US-COPPA" in ids
    assert all(law["jurisdiction"] == "US" for law in matched)


def test_federal_turn_never_surfaces_state_only_laws():
    for domain in _ALL_DOMAINS:
        matched = match_laws("US", domain)
        assert all(
            law["jurisdiction"] == "US" for law in matched
        ), f"US/{domain} surfaced a non-federal law"


# --- Gap 5: cross-domain isolation (negative tests) -------------------------


def test_ca_healthcare_excludes_employment_and_csam():
    matched = match_laws("US-CA", "healthcare")
    matched_domains = {d for law in matched for d in law["matched_domains"]}
    assert matched
    assert matched_domains == {"healthcare"}
    assert not (matched_domains & {"employment", "csam"})


def test_ca_employment_excludes_healthcare_and_csam():
    matched = match_laws("US-CA", "employment")
    matched_domains = {d for law in matched for d in law["matched_domains"]}
    assert matched
    assert matched_domains == {"employment"}
    assert not (matched_domains & {"healthcare", "csam"})


def test_ny_state_turn_excludes_nyc_only_law():
    ids = {law["law_id"] for law in match_laws("US-NY", "employment")}
    assert "US-NYC-AEDT" not in ids


def test_each_single_domain_request_returns_only_that_domain():
    # At least one negative assertion per domain: a single-domain request never
    # leaks laws from any other domain.
    for domain in _ALL_DOMAINS:
        matched = match_laws("US", domain)
        for law in matched:
            assert domain in law["matched_domains"]


# --- Gap 6: future_effective in matching ------------------------------------


def test_future_and_in_force_laws_bucket_correctly():
    today = _today_utc()

    # Mirror production semantics (_split_laws_by_effective_date): a law is
    # future-effective only when it has a parseable YYYY-MM-DD date strictly
    # after today. A missing/blank/None effective_date (e.g. a pending bill)
    # is treated as in-force, so comparisons never assume a string is present.
    def _is_future(effective_date: object) -> bool:
        ed = str(effective_date or "").strip()
        return len(ed) == 10 and ed > today

    # Read effective dates from the data; do not hardcode.
    future_laws = [law for law in STARTER_LAWS if _is_future(law["effective_date"])]
    past_laws = [law for law in STARTER_LAWS if not _is_future(law["effective_date"])]
    assert future_laws, "starter set has no future-effective laws to validate against"
    assert past_laws, "starter set has no in-force laws to validate against"

    sample = future_laws + past_laws
    in_force, future = _split_laws_by_effective_date(sample, today)
    in_ids = {law["law_id"] for law in in_force}
    fut_ids = {law["law_id"] for law in future}

    assert {law["law_id"] for law in future_laws} <= fut_ids
    assert {law["law_id"] for law in past_laws} <= in_ids
    assert in_ids.isdisjoint(fut_ids)
