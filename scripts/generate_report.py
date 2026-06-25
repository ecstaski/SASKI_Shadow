#!/usr/bin/env python3
"""Generate a shadow report from an integrator's own persisted JSONL turn store.

For production shadow deployments: an integrator calls ``analyze_turn()`` inside
their own app, persists each turn with ``result_to_jsonl_turn()`` appended as one
JSON object per line to a JSONL file, then runs this script to produce the report
without re-running a session through ``run_session.py``.

Examples:
    python3 scripts/generate_report.py --input turns.jsonl
    python3 scripts/generate_report.py --input turns.jsonl --outdir out
    python3 scripts/generate_report.py --input turns.jsonl --from 2026-06-01 --to 2026-06-30
    python3 scripts/generate_report.py --input turns.jsonl --last-n 500
    python3 scripts/generate_report.py --input turns.jsonl --session-id abc123

Three files are written to ``<outdir>/report_<timestamp>/``:
    report.json           - full customer-facing report + SDK integration signals
    internal_findings.log - internal-only findings (no per-turn LLM reply flags;
                            raw replies are not stored in JSONL)
    summary.txt           - plain-English summary for a non-technical reader
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from saski_shadow import aggregate_shadow_report  # noqa: E402
from saski_shadow.laws import match_laws  # noqa: E402
from saski_shadow.reporting import generate_html_report  # noqa: E402
from scripts._session_common import (  # noqa: E402
    _build_internal_findings,
    _load_pricing,
    _resolve_outdir,
)


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    """Read a JSONL file into a list of turn dicts.

    Malformed lines are skipped with a warning printed to the console rather than
    crashing the run. Blank lines are ignored silently.
    """
    turns: list[dict] = []
    with open(path, encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"Warning: skipping malformed JSONL line {line_no}: {exc}")
                continue
            if not isinstance(obj, dict):
                print(f"Warning: skipping non-object JSONL line {line_no}")
                continue
            turns.append(obj)
    return turns


def _turn_date(turn: dict) -> str | None:
    """Return the YYYY-MM-DD date portion of a turn's timestamp_utc, or None."""
    ts = turn.get("timestamp_utc")
    if isinstance(ts, str) and len(ts) >= 10:
        return ts[:10]
    return None


def _filter_turns(
    turns: list[dict],
    *,
    session_id: str | None,
    from_date: str | None,
    to_date: str | None,
    last_n: int | None,
) -> list[dict]:
    """Apply session-id, date-range, and last-n filters in that order."""
    result = turns

    if session_id is not None:
        result = [t for t in result if t.get("session_id") == session_id]

    if from_date is not None or to_date is not None:
        kept: list[dict] = []
        for t in result:
            d = _turn_date(t)
            # A date filter requires a usable timestamp; turns without one cannot
            # be placed in range and are excluded.
            if d is None:
                continue
            if from_date is not None and d < from_date:
                continue
            if to_date is not None and d > to_date:
                continue
            kept.append(t)
        result = kept

    if last_n is not None and last_n >= 0:
        result = result[-last_n:] if last_n else []

    return result


def _record_from_turn(turn: dict) -> dict:
    """Build an internal-findings record from a persisted JSONL turn dict."""
    es = turn.get("engine_summary") or {}
    jurisdiction = es.get("user_jurisdiction") or turn.get("jurisdiction")
    ctx_domains = turn.get("domains")
    single = turn.get("domain") or es.get("domain")
    if isinstance(ctx_domains, list) and ctx_domains:
        domain_arg: object = ctx_domains
        # Collapse a 1-element list to a bare string so single-domain turns read
        # the same as in run_session.py (the JSONL always stores domains as a list).
        domain_display = ctx_domains[0] if len(ctx_domains) == 1 else ctx_domains
    else:
        domain_arg = single
        domain_display = single
    matched = match_laws(jurisdiction, domain_arg)
    return {
        "index": turn.get("turn_index"),
        "mode": es.get("mode"),
        "jurisdiction": jurisdiction,
        "domain_display": domain_display,
        "pii": bool(es.get("pii_detected")),
        "pii_span_count": len(es.get("pii_types") or []),
        "escalation": bool(es.get("escalation_detected")),
        "outcome": es.get("outcome"),
        "risk_band": es.get("risk_band"),
        "matched_law_ids": [law["law_id"] for law in matched],
        # reply fields intentionally absent — raw replies are not in JSONL.
    }


def _recommended_next_step(report: dict) -> str:
    """Render the recommended_path section as one plain-English sentence."""
    rec = report["sections"].get("recommended_path", {})
    fs = rec.get("findings_summary", {})
    pii_risk = fs.get("pii_risk", "unknown")
    esc = fs.get("escalation_signal_rate", "unknown")
    latency = "acceptable" if fs.get("latency_acceptable") else "a concern"
    steps = [s for s in rec.get("next_steps", []) if s and s != "Integrator-defined next step"]
    tail = (
        "; ".join(steps)
        if steps
        else (
            "review the full report and contact SASKI Institute to evaluate the "
            "licensed SDK for production enforcement"
        )
    )
    return (
        f"PII risk is {pii_risk}; escalation signal rate is {esc}; latency is "
        f"{latency}. Next: {tail}."
    )


def _build_summary(
    report: dict,
    records: list[dict],
    input_path: pathlib.Path,
    generated_utc: str,
    report_filename: str = "report.json",
) -> str:
    sections = report["sections"]
    pii = sections["pii_phi_detection_summary"]
    compliance = sections["compliance_exposure_examples"]
    escalation = sections["escalation_signal_count"]
    sis = sections["sdk_integration_signals"]
    law_summary = compliance["law_match_summary"]
    period = report.get("period", {})

    pii_types = pii["history_redaction"]["aggregate_pii_types_found"]
    pii_types_str = ", ".join(pii_types) if pii_types else "None"

    jurisdictions = sorted({r["jurisdiction"] for r in records if r["jurisdiction"]})
    jur_str = ", ".join(jurisdictions) if jurisdictions else "None"

    by_outcome = escalation.get("by_outcome", {})
    crisis_turns = by_outcome.get("crisis_referral", 0) + by_outcome.get(
        "physical_emergency_referral", 0
    )

    start = period.get("start_utc") or "unknown"
    end = period.get("end_utc") or "unknown"

    lines = [
        "SASKI Shadow Mode Report Summary",
        f"Generated: {generated_utc}",
        f"Input file: {input_path}",
        f"Turns analyzed: {len(records)}",
        f"Date range: {start} to {end}",
        "",
        "PII DETECTED",
        f"  Turns with PII: {pii['totals']['turns_with_pii']} of "
        f"{pii['totals']['turns_processed']} total",
        f"  PII types found: {pii_types_str}",
        "",
        "COMPLIANCE EXPOSURE",
        f"  Laws matched: {len(law_summary['unique_law_ids'])} unique laws",
        f"  Jurisdictions covered: {jur_str}",
        f"  Future-effective laws: {law_summary['future_effective_count']} "
        "(monitor — not yet enforceable)",
        "",
        "ESCALATION SIGNALS",
        f"  Turns with distress signals: {escalation['totals']['escalation_turns']}",
        f"  Crisis-level turns: {crisis_turns}",
        "",
        "SDK INTEGRATION SIGNALS",
    ]

    signals = sis["signals"]
    lines.append(f"  {len(signals)} signals detected:")
    for sig in signals:
        lines.append(f"  - [{sig['severity']}] {sig['signal_id']}: {sig['title']}")

    lines.extend(
        [
            "",
            "RECOMMENDED NEXT STEP",
            f"  {_recommended_next_step(report)}",
            "",
            f"For the full compliance report see: {report_filename}",
            "For internal findings see: internal_findings.log",
            "Contact SASKI Institute at info@techviz.us or www.techviz.us",
            "for licensed SDK integration support.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a shadow report from a persisted JSONL turn store."
    )
    parser.add_argument("--input", required=True, help="Path to the JSONL turn store.")
    parser.add_argument(
        "--outdir",
        default=None,
        help=(
            "Base output directory. Overrides saski_shadow_config.json output_dir. "
            "Default: outputs/ (or config file value)."
        ),
    )
    parser.add_argument(
        "--from", dest="from_date", default=None, help="ISO date YYYY-MM-DD (inclusive)."
    )
    parser.add_argument(
        "--to", dest="to_date", default=None, help="ISO date YYYY-MM-DD (inclusive)."
    )
    parser.add_argument(
        "--last-n",
        dest="last_n",
        type=int,
        default=None,
        help="Keep only the most recent N turns.",
    )
    parser.add_argument(
        "--session-id",
        dest="session_id",
        default=None,
        help="Keep only turns with this session_id.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "html"],
        default="json",
        help=(
            "Customer report format. 'json' writes report.json (default); "
            "'html' writes report.html instead."
        ),
    )
    parser.add_argument(
        "--pricing",
        default=None,
        help=(
            "Optional path to a pricing JSON (e.g. pricing.json) supplying "
            "token-savings inputs (legacy_system_prompt_tokens, "
            "lean_product_prompt_tokens)."
        ),
    )
    args = parser.parse_args(argv)
    prospect_inputs = _load_pricing(args.pricing)

    input_path = pathlib.Path(args.input)
    if not input_path.is_file():
        raise SystemExit(f"--input file not found or not a file: {input_path}")

    all_turns = _load_jsonl(input_path)
    turns = _filter_turns(
        all_turns,
        session_id=args.session_id,
        from_date=args.from_date,
        to_date=args.to_date,
        last_n=args.last_n,
    )

    if not turns:
        print(
            "No turns remain after filtering — nothing to report. "
            "Check --input, --session-id, --from/--to, and --last-n. "
            "No output files were written."
        )
        return 0

    outdir, outdir_source = _resolve_outdir(args.outdir, _REPO_ROOT)
    generated_utc = _dt.datetime.now(_dt.timezone.utc).isoformat()
    report_id = "report_" + _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = pathlib.Path(outdir) / report_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / ("report.html" if args.format == "html" else "report.json")
    internal_path = run_dir / "internal_findings.log"
    summary_path = run_dir / "summary.txt"

    report = aggregate_shadow_report(turns, prospect_inputs=prospect_inputs)
    if args.format == "html":
        generate_html_report(report, str(report_path))
    else:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    records = [_record_from_turn(t) for t in turns]
    internal_text = _build_internal_findings(
        run_id=report_id,
        provider="none",
        generated_utc=generated_utc,
        total_turns=len(turns),
        records=records,
        error_turns=[],
        sis_signals=report["sections"]["sdk_integration_signals"]["signals"],
        replies_available=False,
    )
    internal_path.write_text(internal_text, encoding="utf-8")

    summary_text = _build_summary(
        report, records, input_path, generated_utc, report_filename=report_path.name
    )
    summary_path.write_text(summary_text, encoding="utf-8")

    period = report.get("period", {})
    date_range = f"{period.get('start_utc') or 'unknown'} to {period.get('end_utc') or 'unknown'}"
    report_label = f"{report_path.name:<21}"
    print(f"Report generated from {len(turns)} turns ({date_range})")
    print(f"Output directory: {run_dir}  (source: {outdir_source})")
    print(f"  {report_label} — customer-facing compliance report")
    print("  internal_findings.log — internal use only")
    print("  summary.txt           — plain-English summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
