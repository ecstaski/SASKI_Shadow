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
    load_turns_jsonl,
    result_to_jsonl_turn,
)
from saski_shadow.analyzer import analyze_turn  # noqa: E402


def _load_session(path: str | None) -> list[dict]:
    if path:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise SystemExit(f"session file {path} must contain a JSON list of turns")
        return data
    from harness.fixtures.canonical_session import CANONICAL_SESSION

    return list(CANONICAL_SESSION)


def _send_to_provider(provider: str, prompt: str) -> str:
    """Send the redacted prompt to a live provider; return the reply text."""
    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        resp = client.messages.create(
            model=os.environ.get("SASKI_ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
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
        default=str(_REPO_ROOT / "outputs"),
        help="Base output directory (default: ./outputs).",
    )
    args = parser.parse_args(argv)

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

    session = _load_session(args.session)

    run_id = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = pathlib.Path(args.outdir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = run_dir / "turns.jsonl"
    log_path = run_dir / "session.log"
    report_path = run_dir / "report.json"

    session_id = f"runner_{run_id}"
    log_lines: list[str] = [
        f"# shadow session run {run_id}",
        f"# provider: {args.provider}",
        f"# turns: {len(session)}",
        "",
    ]

    with open(jsonl_path, "w", encoding="utf-8") as jsonl_handle:
        for index, raw in enumerate(session):
            message = raw.get("message", "")
            context = dict(raw.get("session_context") or {})
            if "extra_distress_indicators" in raw:
                context.setdefault("extra_distress_indicators", raw["extra_distress_indicators"])
            mode = context.get("mode")

            result = analyze_turn(message, session_context=context, mode=mode)
            turn = result_to_jsonl_turn(
                result, session_id=session_id, turn_index=index, provider_id=args.provider
            )
            # Preserve a multi-domain turn so the report can surface every domain.
            if isinstance(context.get("domains"), list):
                turn["domains"] = list(context["domains"])
            jsonl_handle.write(json.dumps(turn) + "\n")

            summary = result.metadata["engine_summary"]
            reply = None
            if args.provider != "none":
                try:
                    reply = _send_to_provider(args.provider, result.message_for_llm or "")
                except Exception as exc:  # noqa: BLE001 - surface, do not crash the run
                    reply = f"<provider error: {exc}>"

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
    report = aggregate_shadow_report(turns)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

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
    print(f"  turns.jsonl:            {jsonl_path}")
    print(f"  session.log:            {log_path}")
    print(f"  report.json:            {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
