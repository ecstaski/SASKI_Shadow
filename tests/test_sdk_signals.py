"""Tests for sdk_integration_signals section in aggregate shadow reports."""

from __future__ import annotations

from saski_shadow.aggregate.report import aggregate_shadow_report

# ---------------------------------------------------------------------------
# Shared turn-builder helpers
# ---------------------------------------------------------------------------

def _turn(
    index: int,
    session_id: str = "sess_x",
    *,
    pii: bool = False,
    pii_types: list[str] | None = None,
    escalation: bool = False,
    would_block: bool = False,
    jurisdiction: str | None = None,
    domain: str | None = None,
    domains: list[str] | None = None,
) -> dict:
    t: dict = {
        "turn_index": index,
        "session_id": session_id,
        "latency_ms": 10.0,
        "mode_tag": "shadow_mode",
        "envelope": {},
        "transport_audit_record": {
            "jurisdiction_source": "integrator_supplied" if jurisdiction else "not_provided",
            "pii_types": pii_types or [],
        },
        "compliance_decisions": [],
        "output_review": {},
        "deployment_decision": None,
        "engine_summary": {
            "outcome": "allow",
            "risk_band": "low",
            "governance_tier": "tier_clean",
            "pii_detected": pii,
            "pii_types": pii_types or [],
            "escalation_detected": escalation,
            "would_block": would_block,
            "user_jurisdiction": jurisdiction,
            "domain": domain,
            "mode": None,
            "phase_timings": {},
        },
    }
    if jurisdiction:
        t["jurisdiction"] = jurisdiction
    if domains:
        t["domains"] = domains
    elif domain:
        t["domain"] = domain
    return t


def _report(turns: list[dict]) -> dict:
    return aggregate_shadow_report(turns)


# ---------------------------------------------------------------------------
# Task 1 — SIS-001: escalation triggers signal
# ---------------------------------------------------------------------------

def test_sis001_fires_when_escalation_turns_present():
    turns = [
        _turn(0, escalation=True),
        _turn(1),
    ]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-001" in ids


def test_sis001_not_emitted_when_no_escalation():
    turns = [_turn(0), _turn(1)]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-001" not in ids


def test_sis001_observation_contains_escalation_count():
    turns = [_turn(0, escalation=True), _turn(1, escalation=True)]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    sig = next(s for s in sis["signals"] if s["signal_id"] == "SIS-001")
    assert "2 escalation signals" in sig["observation"]


# ---------------------------------------------------------------------------
# Task 1 — SIS-004: PII turns trigger signal
# ---------------------------------------------------------------------------

def test_sis004_fires_when_pii_detected():
    turns = [
        _turn(0, pii=True, pii_types=["ssn"]),
        _turn(1),
    ]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-004" in ids


def test_sis004_observation_mentions_pii_type():
    turns = [_turn(0, pii=True, pii_types=["email"])]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    sig = next(s for s in sis["signals"] if s["signal_id"] == "SIS-004")
    assert "email" in sig["observation"]
    assert "1 turn" in sig["observation"]


def test_sis004_not_emitted_when_no_pii():
    turns = [_turn(0), _turn(1), _turn(2)]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-004" not in ids


# ---------------------------------------------------------------------------
# Task 1 — SIS-002: future-effective laws trigger signal
# ---------------------------------------------------------------------------

def test_sis002_fires_when_future_effective_law_matched():
    # US-TX has a future-effective law (TX-CONSUMER-BOT-DISCLOSURE-2026-FUTURE)
    # if the current date is before its effective_date.
    turns = [
        _turn(0, jurisdiction="US-TX", domain="consumer_chatbot"),
    ]
    report = _report(turns)
    compliance = report["sections"]["compliance_exposure_examples"]
    future = compliance["matched_laws_by_status"]["future_effective"]
    sis = report["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    if future:
        assert "SIS-002" in ids
    else:
        assert "SIS-002" not in ids


# ---------------------------------------------------------------------------
# Task 1 — SIS-003: multi-domain turns trigger signal
# ---------------------------------------------------------------------------

def test_sis003_fires_when_multi_domain_turn_present():
    turns = [
        _turn(0, jurisdiction="US-CA", domains=["consumer_chatbot", "csam"]),
        _turn(1),
    ]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-003" in ids


def test_sis003_not_emitted_for_single_domain_session():
    turns = [
        _turn(0, jurisdiction="US-CA", domain="healthcare"),
        _turn(1, jurisdiction="US-CA", domain="healthcare"),
    ]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    ids = [s["signal_id"] for s in sis["signals"]]
    assert "SIS-003" not in ids


# ---------------------------------------------------------------------------
# Task 1 — zero signals case
# ---------------------------------------------------------------------------

def test_zero_signals_returns_empty_list_and_correct_summary():
    # Single turn, no PII, no escalation, no jurisdiction/domain, <=5 turns
    turns = [_turn(i) for i in range(3)]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    assert sis["signals"] == []
    assert sis["summary"] == "No integration signals detected for this session"


# ---------------------------------------------------------------------------
# Task 1 — contact field on every emitted signal
# ---------------------------------------------------------------------------

def test_every_emitted_signal_has_correct_contact():
    turns = [
        _turn(0, pii=True, pii_types=["ssn"]),
        _turn(1, escalation=True),
        _turn(2, jurisdiction="US-CA", domains=["consumer_chatbot", "csam"]),
        _turn(3, jurisdiction="US-CA", domain="healthcare"),
        _turn(4),
        _turn(5),
        _turn(6),
    ]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    assert sis["signals"], "expected at least one signal"
    for sig in sis["signals"]:
        assert sig["contact"] == "support@saski.io", (
            f"{sig['signal_id']} has wrong contact: {sig['contact']!r}"
        )


# ---------------------------------------------------------------------------
# Task 1 — summary string format
# ---------------------------------------------------------------------------

def test_summary_reflects_signal_and_category_counts():
    turns = [_turn(0, pii=True, pii_types=["email"]), _turn(1, escalation=True)]
    sis = _report(turns)["sections"]["sdk_integration_signals"]
    assert sis["summary"].startswith("2 integration signals")


# ---------------------------------------------------------------------------
# Task 1 — section key present and schema-compatible
# ---------------------------------------------------------------------------

def test_sdk_integration_signals_section_present_in_report():
    report = _report([_turn(0)])
    assert "sdk_integration_signals" in report["sections"]
    sis = report["sections"]["sdk_integration_signals"]
    assert "section" in sis
    assert sis["section"] == "sdk_integration_signals"
    assert "summary" in sis
    assert "signals" in sis


# _resolve_outdir tests removed with internal scripts/run_session.py (maintainer-only).
# Output-directory resolution is not part of the public saski_shadow package API.
