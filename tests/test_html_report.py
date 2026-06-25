"""Tests for the self-contained HTML report renderer."""

from __future__ import annotations

from saski_shadow import aggregate_shadow_report
from saski_shadow.reporting import generate_html_report
from saski_shadow.reporting.html_report import render_html_report

HEX64 = "a" * 64


def _turn(idx, session_id="sess_html", *, tier="tier_clean", mode=None,
          pii_types=None, escalation=False, jurisdiction=None, domain=None):
    return {
        "turn_index": idx,
        "timestamp_utc": "2026-06-12T16:00:00+00:00",
        "session_id": session_id,
        "input_hash": HEX64,
        "mode_tag": "shadow_mode",
        "latency_ms": 2.0,
        "envelope": {},
        "transport_audit_record": {"pii_types": pii_types or [],
                                   "redaction_applied": bool(pii_types)},
        "engine_summary": {
            "outcome": "allow",
            "risk_band": "low",
            "pii_detected": bool(pii_types),
            "pii_types": pii_types or [],
            "escalation_detected": escalation,
            "would_block": False,
            "governance_tier": tier,
            "mode": mode,
            "user_jurisdiction": jurisdiction,
            "domain": domain,
            "phase_timings": {"stage_one": 1.0},
        },
    }


def _report():
    turns = [
        _turn(0, mode="patient", pii_types=["email"], jurisdiction="US-CA",
              domain="healthcare"),
        _turn(1, tier="tier_warning", escalation=True, jurisdiction="US-CA",
              domain="healthcare"),
    ]
    return aggregate_shadow_report(
        turns,
        prospect_inputs={"legacy_system_prompt_tokens": 450,
                         "lean_product_prompt_tokens": 103},
        latency_targets={"integrator_p95_target_ms": 50.0},
    )


def test_renders_valid_self_contained_html():
    html = render_html_report(_report())
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    # Self-contained: no external assets / network calls.
    assert "http://" not in html
    assert "https://" not in html
    assert "<script" not in html.lower()
    assert "<style>" in html


def test_renders_all_nine_sections_and_cover():
    html = render_html_report(_report())
    titles = [
        "SASKI Shadow Pilot Report",
        "1. PII / PHI Detection Summary",
        "2. Compliance Exposure Examples",
        "3. Token Savings Calculation",
        "4. Envelope Evidence Sample",
        "5. Escalation Signal Count",
        "6. Unsafe Flow Documentation",
        "7. Latency Impact Report",
        "8. Recommended Path",
        "9. SDK Integration Signals",
    ]
    for title in titles:
        assert title in html, f"missing section: {title}"


def test_branding_is_saski_institute_pbc_only():
    html = render_html_report(_report())
    assert "SASKI Institute PBC" in html
    assert "info@techviz.us" in html
    assert "Technical Visionaries" not in html


def test_observation_only_language_present_no_enforcement_claims():
    html = render_html_report(_report())
    assert "did not block, modify, or suppress" in html
    assert "Absence of a finding is not evidence of compliance." in html
    lowered = html.lower()
    for forbidden in ("we blocked", "we redacted", "we enforced", "we prevented"):
        assert forbidden not in lowered


def test_session_id_surfaced_on_cover():
    html = render_html_report(_report())
    assert "sess_html" in html


def test_token_savings_values_rendered():
    html = render_html_report(_report())
    assert "Total tokens saved (estimate)" in html
    # Tier 3 escalation credits full legacy; dollar note present, no dollar sign math.
    assert "Dollar savings = tokens_saved" in html


def test_generate_html_report_writes_file(tmp_path):
    out = tmp_path / "report.html"
    returned = generate_html_report(_report(), str(out))
    assert out.is_file()
    written = out.read_text(encoding="utf-8")
    assert written == returned
    assert written.startswith("<!DOCTYPE html>")


def test_insufficient_inputs_report_still_renders():
    # No pricing -> token savings basis insufficient; renderer must not crash.
    report = aggregate_shadow_report([_turn(0)])
    html = render_html_report(report)
    assert "insufficient_inputs" in html
    assert "3. Token Savings Calculation" in html
