#!/usr/bin/env python3
"""Run a shadow session end-to-end and write inspectable output files.

For each turn it runs the real pipeline:

    analyze_turn() -> result_to_jsonl_turn() -> append JSONL
    (optional) send the redacted message_for_llm to a live provider
    aggregate_shadow_report() over the persisted turns

and writes everything under ``outputs/<run-id>/``:

    turns.jsonl   - the persisted turn store the aggregator consumes
    session.log   - human-readable per-turn trace
    report.json   - the generated 8-section shadow report

The ``outputs/`` directory is gitignored. Only the redacted ``message_for_llm``
is ever sent to a provider; raw PII never leaves the pipeline.

Examples:
    python scripts/run_session.py                       # canonical session, no LLM
    python scripts/run_session.py --provider anthropic  # live LLM in the loop
    python scripts/run_session.py --session my.json     # custom session file
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# Make the harness fixtures importable the same way pytest sees them.
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "tests"))

from saski_shadow import (  # noqa: E402
    aggregate_shadow_report,
    compute_output_hash,
    load_turns_jsonl,
    result_to_jsonl_turn,
)
from saski_shadow.analyzer import analyze_turn  # noqa: E402
from saski_shadow.detectors.output_review import review_output  # noqa: E402
from saski_shadow.laws import match_laws  # noqa: E402
from saski_shadow.reporting import generate_html_report  # noqa: E402

# Shared with generate_report.py; re-exported here so existing callers/tests that
# import ``scripts.run_session._resolve_outdir`` keep working.
from scripts._session_common import (  # noqa: E402
    _build_internal_findings,
    _load_pricing,
    _resolve_outdir,
)


def _load_session(path: str | None) -> list[dict]:
    if path:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise SystemExit(f"session file {path} must contain a JSON list of turns")
        return data
    from harness.fixtures.canonical_session import CANONICAL_SESSION

    return list(CANONICAL_SESSION)


def _send_to_provider(provider: str, prompt: str) -> str:
    """Send the redacted prompt to a live provider; return the reply text.

    Model selection: each provider reads an optional environment variable
    (SASKI_ANTHROPIC_MODEL / SASKI_OPENAI_MODEL) and falls back to a
    currently-valid default below. To use a different model for a single run,
    prefix the command, e.g.::

        SASKI_ANTHROPIC_MODEL=claude-sonnet-4-6 python3 scripts/run_session.py ...
    """
    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=os.environ.get("SASKI_ANTHROPIC_MODEL", "claude-haiku-4-5"),
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        resp = client.chat.completions.create(
            model=os.environ.get("SASKI_OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or ""
    raise SystemExit(f"unknown provider: {provider!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a shadow session end-to-end.")
    parser.add_argument(
        "--provider",
        choices=["none", "anthropic", "openai"],
        default="none",
        help="LLM provider to send redacted payloads to (default: none).",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Path to a JSON session file. Defaults to the canonical session.",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help=(
            "Base output directory. Overrides saski_shadow_config.json output_dir. "
            "Default: outputs/ (or config file value)."
        ),
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

    # Load .env so provider keys are available when run as a script.
    try:
        from dotenv import load_dotenv

        env_path = _REPO_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    if args.provider != "none":
        key = "ANTHROPIC_API_KEY" if args.provider == "anthropic" else "OPENAI_API_KEY"
        if not os.environ.get(key):
            raise SystemExit(f"--provider {args.provider} requires {key} to be set")

    outdir, outdir_source = _resolve_outdir(args.outdir, _REPO_ROOT)
    print(f"Output directory: {outdir}  (source: {outdir_source})")

    session = _load_session(args.session)

    run_id = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = pathlib.Path(outdir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = run_dir / "turns.jsonl"
    log_path = run_dir / "session.log"
    report_path = run_dir / ("report.html" if args.format == "html" else "report.json")
    internal_path = run_dir / "internal_findings.log"

    session_id = f"runner_{run_id}"
    log_lines: list[str] = [
        f"# shadow session run {run_id}",
        f"# provider: {args.provider}",
        f"# turns: {len(session)}",
        "",
    ]
    # Per-turn records feed internal_findings.log only; never session.log/report.
    records: list[dict] = []
    error_turns: list[int] = []

    with open(jsonl_path, "w", encoding="utf-8") as jsonl_handle:
        for index, raw in enumerate(session):
            message = raw.get("message", "")
            context = dict(raw.get("session_context") or {})
            if "extra_distress_indicators" in raw:
                context.setdefault("extra_distress_indicators", raw["extra_distress_indicators"])
            mode = context.get("mode")

            try:
                result = analyze_turn(message, session_context=context, mode=mode)
                turn = result_to_jsonl_turn(
                    result, session_id=session_id, turn_index=index, provider_id=args.provider
                )
                # Preserve a multi-domain turn so the report can surface every domain.
                if isinstance(context.get("domains"), list):
                    turn["domains"] = list(context["domains"])
            except Exception as exc:  # noqa: BLE001 - record and continue, don't crash run
                error_turns.append(index)
                log_lines.extend([f"--- turn {index} ---", f"ERROR: {exc}", ""])
                continue

            summary = result.metadata["engine_summary"]
            reply = None
            if args.provider != "none":
                try:
                    reply = _send_to_provider(args.provider, result.message_for_llm or "")
                except Exception as exc:  # noqa: BLE001 - surface, do not crash the run
                    reply = f"<provider error: {exc}>"
            reply_is_error = bool(reply) and reply.startswith("<provider error:")

            # Post-LLM output review: feed the actual model reply back through the
            # same observable review used on inputs, so the report's unsafe-flow
            # section reflects model behavior (PII leaked back into the output,
            # claimed human escalation) instead of staying empty. Only run on a
            # real reply; provider errors and no-provider runs leave it untouched.
            if reply is not None and not reply_is_error:
                review = review_output(reply, input_pii_types=list(result.pii_types or []))
                turn["output_review"] = {
                    "pii_leaked_types": review.pii_leaked_types,
                    "human_escalation_claimed": review.human_escalation_claimed,
                    "policy_boundary_hits": review.policy_boundary_hits,
                    "findings": review.findings,
                }
                # Record the real reply hash as evidence for the reviewed output.
                turn["output_hash"] = compute_output_hash(reply)

            jsonl_handle.write(json.dumps(turn) + "\n")

            ctx_domains = context.get("domains")
            domain_display = ctx_domains or summary.get("domain")
            domain_arg = ctx_domains if isinstance(ctx_domains, list) else summary.get("domain")
            matched = match_laws(summary.get("user_jurisdiction"), domain_arg)
            records.append(
                {
                    "index": index,
                    "mode": summary.get("mode"),
                    "jurisdiction": summary.get("user_jurisdiction"),
                    "domain_display": domain_display,
                    "message": message,
                    "redacted": result.message_for_llm,
                    "reply": reply,
                    "reply_is_error": reply_is_error,
                    "pii": bool(summary.get("pii_detected")),
                    "pii_span_count": len(summary.get("pii_types") or []),
                    "escalation": bool(summary.get("escalation_detected")),
                    "outcome": summary.get("outcome"),
                    "risk_band": summary.get("risk_band"),
                    "matched_law_ids": [law["law_id"] for law in matched],
                }
            )

            log_lines.extend(
                [
                    f"--- turn {index} ---",
                    f"mode:          {summary.get('mode')}",
                    f"jurisdiction:  {summary.get('user_jurisdiction')}",
                    f"domain(s):     {context.get('domains') or summary.get('domain')}",
                    f"outcome:       {summary.get('outcome')}",
                    f"risk_band:     {summary.get('risk_band')}",
                    f"pii_detected:  {summary.get('pii_detected')}",
                    f"pii_types:     {summary.get('pii_types')}",
                    f"escalation:    {summary.get('escalation_detected')}",
                    f"redacted_msg:  {result.message_for_llm}",
                ]
            )
            if reply is not None:
                log_lines.append(f"llm_reply:     {reply.strip()}")
            log_lines.append("")

    turns = load_turns_jsonl(str(jsonl_path))
    report = aggregate_shadow_report(turns, prospect_inputs=prospect_inputs)
    if args.format == "html":
        generate_html_report(report, str(report_path))
    else:
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    sis = report["sections"]["sdk_integration_signals"]
    log_lines.append("=== SDK INTEGRATION SIGNALS ===")
    if sis["signals"]:
        for sig in sis["signals"]:
            sev_label = f"[{sig['severity']}]"
            log_lines.append(f"{sev_label:<18} {sig['signal_id']}: {sig['title']}")
            log_lines.append(f"{'':18} Observation: {sig['observation']}")
            log_lines.append(f"{'':18} Recommendation: {sig['sdk_recommendation']}")
            log_lines.append("")
        log_lines.append("Contact info@techviz.us for licensed SDK integration support.")
    else:
        log_lines.append("No integration signals detected for this session.")
    log_lines.append("================================")

    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # internal_findings.log — dev-only, written separately so none of its content
    # ever lands in session.log or report.json above.
    internal_text = _build_internal_findings(
        run_id=run_id,
        provider=args.provider,
        generated_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        total_turns=len(session),
        records=records,
        error_turns=error_turns,
        sis_signals=sis["signals"],
    )
    internal_path.write_text(internal_text, encoding="utf-8")

    compliance = report["sections"]["compliance_exposure_examples"]
    pii = report["sections"]["pii_phi_detection_summary"]
    escalation = report["sections"]["escalation_signal_count"]
    law_summary = compliance["law_match_summary"]

    print(f"Run {run_id} complete -> {run_dir}")
    print(f"  turns processed:        {len(turns)}")
    print(f"  turns with PII:         {pii['totals']['turns_with_pii']}")
    print(f"  escalation turns:       {escalation['totals']['escalation_turns']}")
    print(f"  unique laws matched:    {len(law_summary['unique_law_ids'])}")
    print(f"  future-effective laws:  {law_summary['future_effective_count']}")
    print(f"  provider:               {args.provider}")
    report_label = "report.html:" if args.format == "html" else "report.json:"
    print(f"  turns.jsonl:            {jsonl_path}")
    print(f"  session.log:            {log_path}")
    print(f"  {report_label:<22}  {report_path}")
    print(f"  internal_findings.log:  {internal_path}  (INTERNAL ONLY)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
