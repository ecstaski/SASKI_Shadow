"""Tests for scripts/generate_report.py and the PII-spans internal metric."""

from __future__ import annotations

import json
import pathlib


def _gr_main():
    """Import generate_report.main, adding repo root to sys.path first."""
    import sys

    repo = pathlib.Path(__file__).resolve().parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from scripts.generate_report import main  # noqa: E402

    return main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _turn(
    index: int,
    session_id: str = "s1",
    *,
    pii_types: list[str] | None = None,
    escalation: bool = False,
    jurisdiction: str | None = None,
    domain: str | None = None,
    domains: list[str] | None = None,
    timestamp: str | None = None,
) -> dict:
    es = {
        "outcome": "allow",
        "risk_band": "low",
        "governance_tier": "tier_clean",
        "pii_detected": bool(pii_types),
        "pii_types": pii_types or [],
        "escalation_detected": escalation,
        "would_block": False,
        "user_jurisdiction": jurisdiction,
        "domain": domain,
        "domains": domains or ([domain] if domain else []),
        "mode": None,
        "phase_timings": {},
    }
    t: dict = {
        "turn_index": index,
        "session_id": session_id,
        "timestamp_utc": timestamp,
        "latency_ms": 10.0,
        "mode_tag": "shadow_mode",
        "envelope": {},
        "transport_audit_record": {"pii_types": pii_types or []},
        "compliance_decisions": [],
        "output_review": {},
        "deployment_decision": None,
        "engine_summary": es,
    }
    if jurisdiction:
        t["jurisdiction"] = jurisdiction
    if domains:
        t["domains"] = domains
    elif domain:
        t["domain"] = domain
    return t


def _write_jsonl(path: pathlib.Path, turns: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(t) for t in turns) + "\n", encoding="utf-8")


def _run(tmp_path: pathlib.Path, jsonl: pathlib.Path, *extra: str):
    out = tmp_path / "out"
    rc = _gr_main()(["--input", str(jsonl), "--outdir", str(out), *extra])
    report_dirs = sorted(out.glob("report_*")) if out.exists() else []
    return rc, out, report_dirs


def _report_json(report_dir: pathlib.Path) -> dict:
    return json.loads((report_dir / "report.json").read_text(encoding="utf-8"))


def _turns_processed(report_dir: pathlib.Path) -> int:
    report = _report_json(report_dir)
    return report["sections"]["pii_phi_detection_summary"]["totals"]["turns_processed"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_produces_all_three_output_files(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(i, jurisdiction="US-CA", domain="healthcare") for i in range(3)])

    rc, _out, report_dirs = _run(tmp_path, jsonl)
    assert rc == 0
    assert len(report_dirs) == 1
    d = report_dirs[0]
    assert (d / "report.json").is_file()
    assert (d / "internal_findings.log").is_file()
    assert (d / "summary.txt").is_file()


def test_last_n_keeps_only_most_recent(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(i) for i in range(10)])

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--last-n", "3")
    assert rc == 0
    assert _turns_processed(report_dirs[0]) == 3


def test_session_id_filter(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    turns = [_turn(0, "alpha"), _turn(1, "beta"), _turn(2, "alpha"), _turn(3, "gamma")]
    _write_jsonl(jsonl, turns)

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--session-id", "alpha")
    assert rc == 0
    assert _turns_processed(report_dirs[0]) == 2


def test_date_range_filter(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    turns = [
        _turn(0, timestamp="2026-06-01T10:00:00+00:00"),
        _turn(1, timestamp="2026-06-15T10:00:00+00:00"),
        _turn(2, timestamp="2026-06-30T10:00:00+00:00"),
    ]
    _write_jsonl(jsonl, turns)

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--from", "2026-06-10", "--to", "2026-06-20")
    assert rc == 0
    assert _turns_processed(report_dirs[0]) == 1


def test_malformed_line_skipped_without_crashing(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    good = [_turn(0), _turn(1)]
    text = json.dumps(good[0]) + "\n" + "{not valid json,,," + "\n" + json.dumps(good[1]) + "\n"
    jsonl.write_text(text, encoding="utf-8")

    rc, _out, report_dirs = _run(tmp_path, jsonl)
    assert rc == 0
    # Two good turns survive; the malformed middle line is skipped.
    assert _turns_processed(report_dirs[0]) == 2


def test_zero_turns_after_filter_exits_without_writing(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(0, "alpha"), _turn(1, "alpha")])

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--session-id", "does-not-exist")
    assert rc == 0
    assert report_dirs == []


def test_avg_pii_spans_counts_spans_not_zero(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    # One turn carrying two PII types -> 2 spans across 1 turn -> 2.0 per turn.
    _write_jsonl(jsonl, [_turn(0, pii_types=["ssn", "email"])])

    rc, _out, report_dirs = _run(tmp_path, jsonl)
    assert rc == 0
    internal = (report_dirs[0] / "internal_findings.log").read_text(encoding="utf-8")
    assert "Avg PII spans redacted per turn: 2.0" in internal


def test_quality_flags_section_marked_unavailable(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(0)])

    rc, _out, report_dirs = _run(tmp_path, jsonl)
    assert rc == 0
    internal = (report_dirs[0] / "internal_findings.log").read_text(encoding="utf-8")
    assert "raw LLM replies are not persisted in JSONL" in internal
    assert "Turns with LLM call:             n/a (not persisted in JSONL)" in internal


def test_input_file_missing_exits_with_error(tmp_path):
    missing = tmp_path / "nope.jsonl"
    try:
        _gr_main()(["--input", str(missing), "--outdir", str(tmp_path / "out")])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("expected SystemExit for a missing input file")


def test_format_html_writes_report_html_instead_of_json(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(i, jurisdiction="US-CA", domain="healthcare") for i in range(2)])

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--format", "html")
    assert rc == 0
    d = report_dirs[0]
    assert (d / "report.html").is_file()
    assert not (d / "report.json").exists()
    html = (d / "report.html").read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "SASKI Institute PBC" in html


def test_pricing_populates_prospect_inputs(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(i) for i in range(2)])
    pricing = tmp_path / "pricing.json"
    pricing.write_text(
        json.dumps(
            {"legacy_system_prompt_tokens": 450, "lean_product_prompt_tokens": 103}
        ),
        encoding="utf-8",
    )

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--pricing", str(pricing))
    assert rc == 0
    section = _report_json(report_dirs[0])["sections"]["token_savings_calculation"]
    assert section["basis"] == "estimated_from_integrator_inputs"
    assert section["prospect_inputs"]["legacy_system_prompt_tokens"] == 450.0
    # 2 clean non-regulated turns: each saves 450-103=347 -> 694.
    assert section["savings"]["tokens_saved_estimate"] == 694.0


def test_pricing_accepts_wrapped_prospect_inputs(tmp_path):
    jsonl = tmp_path / "turns.jsonl"
    _write_jsonl(jsonl, [_turn(0)])
    pricing = tmp_path / "pricing.json"
    pricing.write_text(
        json.dumps(
            {"prospect_inputs": {"legacy_system_prompt_tokens": 200,
                                 "lean_product_prompt_tokens": 50}}
        ),
        encoding="utf-8",
    )

    rc, _out, report_dirs = _run(tmp_path, jsonl, "--pricing", str(pricing))
    assert rc == 0
    section = _report_json(report_dirs[0])["sections"]["token_savings_calculation"]
    assert section["prospect_inputs"]["lean_product_prompt_tokens"] == 50.0
