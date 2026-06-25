"""Shared helpers for the shadow session tooling scripts.

Both ``run_session.py`` (fixed-session test runner) and ``generate_report.py``
(report generator over an integrator's own persisted JSONL) import from here so
the output-directory resolution and the internal_findings.log format live in one
place. None of this is part of the public ``saski_shadow`` package surface — it
is script-level tooling only.
"""

from __future__ import annotations

import json
import pathlib


def _resolve_outdir(
    cli_outdir: str | None,
    repo_root: pathlib.Path,
) -> tuple[str, str]:
    """Return ``(outdir_path, source_label)``.

    Precedence: CLI ``--outdir`` flag > ``saski_shadow_config.json`` output_dir
    > default ``outputs/``. ``source_label`` is one of ``cli_flag``,
    ``config_file``, or ``default``.
    """
    if cli_outdir is not None:
        return cli_outdir, "cli_flag"
    config_path = repo_root / "saski_shadow_config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            output_dir = cfg.get("output_dir")
            if isinstance(output_dir, str) and output_dir:
                return output_dir, "config_file"
        except (json.JSONDecodeError, OSError):
            pass
    return str(repo_root / "outputs"), "default"


def _load_pricing(path: str | None) -> dict:
    """Load an integrator-supplied pricing/token-model JSON for ``--pricing``.

    The file may either be a flat object of ``prospect_inputs`` fields (e.g.
    ``{"legacy_system_prompt_tokens": 450, ...}``) or wrap them under a
    top-level ``prospect_inputs`` key. Returns the dict passed straight to
    ``aggregate_shadow_report(prospect_inputs=...)``. An empty/None path yields
    an empty dict so callers can always splat the result.
    """
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Pricing file must contain a JSON object at the top level.")
    inner = data.get("prospect_inputs")
    if isinstance(inner, dict):
        return inner
    return data


# --- Internal findings (dev-only) -------------------------------------------
# The helpers below produce internal_findings.log, an internal output file for
# the SASKI team / Stephen only. It is never shown to customers and its content
# never appears in report.json or session.log.

# Plain-language legal-concept markers used to decide whether an LLM reply even
# acknowledged that law might apply. Heuristic triage aid only — not a compliance
# determination.
_LEGAL_CONCEPT_TERMS = (
    "law",
    "legal",
    "regulation",
    "regulat",
    "statute",
    "right",
    "compliance",
    "privacy",
    "consent",
    "disclosure",
    "attorney",
    "court",
    "liable",
    "liability",
    "jurisdiction",
    "illegal",
    "prohibited",
    "require",
    "protected",
    "confidential",
    "hipaa",
    "coppa",
    "ccpa",
    "gdpr",
)

# Minimal state-code -> spoken-name map so a reply that names the state counts as
# referencing the jurisdiction. Extend as needed; absence just means the legal
# terms above carry the check.
_STATE_NAMES = {
    "US-CA": "california",
    "US-NY": "new york",
    "US-TX": "texas",
    "US-FL": "florida",
    "US-IL": "illinois",
    "US-WA": "washington",
    "US-CO": "colorado",
    "US-UT": "utah",
    "US-VA": "virginia",
    "US-MA": "massachusetts",
    "US-NJ": "new jersey",
    "US-PA": "pennsylvania",
}

# Internal action note per SIS signal. Mirrors the customer signal IDs but tells
# the team what to actually check — no customer-facing recommendation text.
_SIS_INTERNAL_ACTIONS = {
    "SIS-001": (
        "Verify licensed SDK distress detection is configured for this mode and "
        "jurisdiction before production deployment"
    ),
    "SIS-002": (
        "Add future-effective law dates to SDK jurisdiction update schedule — "
        "contact registry team"
    ),
    "SIS-003": "Verify integration is passing domains list correctly in session_context per turn",
    "SIS-004": (
        "Verify licensed SDK PII redaction tier is configured for this mode — "
        "check compliance_matrix"
    ),
    "SIS-005": (
        "Run axis3 cross-domain isolation tests before customer demo or production deployment"
    ),
    "SIS-006": (
        "Run a dedicated crisis detection test session using the licensed SDK "
        "before production deployment"
    ),
}

# Characters that count as a complete sentence ending for truncation detection.
_END_PUNCT = ".!?\"')]:;…"

# Message shown for the LLM RESPONSE QUALITY FLAGS section when raw replies are
# not available (e.g. when generating a report from persisted JSONL).
_QUALITY_FLAGS_UNAVAILABLE = (
    "Not available — raw LLM replies are not persisted in JSONL. "
    "Run via run_session.py to capture LLM response quality flags."
)


def _excerpt(text: str | None, limit: int) -> str:
    """First ``limit`` characters of ``text`` on one line (newlines flattened)."""
    return (text or "").strip().replace("\n", " ")[:limit]


def _collapse_state(jurisdiction: str) -> str:
    """Collapse a jurisdiction to its state level (``US-NY-NYC`` -> ``US-NY``)."""
    parts = [p for p in jurisdiction.split("-") if p]
    return "-".join(parts[:2]) if len(parts) >= 2 else jurisdiction


def _references_law_or_jurisdiction(reply: str, jurisdiction: str | None) -> bool:
    """True if the reply mentions any legal concept or names its jurisdiction."""
    low = reply.lower()
    if any(term in low for term in _LEGAL_CONCEPT_TERMS):
        return True
    if jurisdiction:
        if jurisdiction == "US" and "federal" in low:
            return True
        name = _STATE_NAMES.get(_collapse_state(jurisdiction))
        if name and name in low:
            return True
    return False


def _flags_for_turn(rec: dict, provider: str) -> list[str]:
    """Return the LLM-response quality flags that fire for one turn record.

    Reply-based flags only apply when an actual (non-error) LLM reply exists,
    i.e. a provider was used and the call succeeded.
    """
    flags: list[str] = []
    reply = rec.get("reply")
    evaluable = provider != "none" and reply is not None and not rec.get("reply_is_error")
    if not evaluable:
        return flags

    stripped = reply.strip()
    low = stripped.lower()

    if stripped == "" or (len(stripped) < 200 and stripped[-1] not in _END_PUNCT):
        flags.append("TRUNCATED_RESPONSE")
    if (
        rec.get("outcome") == "allow"
        and rec.get("risk_band") == "low"
        and ("i cannot" in low or "i can't" in low)
    ):
        flags.append("UNNECESSARY_REFUSAL")
    if rec.get("matched_law_ids") and not _references_law_or_jurisdiction(
        stripped, rec.get("jurisdiction")
    ):
        flags.append("POSSIBLE_LAW_COMPLIANCE_GAP")
    if rec.get("escalation") and not any(kw in low for kw in ("988", "crisis", "help")):
        flags.append("MISSING_CRISIS_LANGUAGE")
    return flags


def _build_internal_findings(
    run_id: str,
    provider: str,
    generated_utc: str,
    total_turns: int,
    records: list[dict],
    error_turns: list[int],
    sis_signals: list[dict],
    *,
    replies_available: bool = True,
) -> str:
    """Assemble the full internal_findings.log text from collected turn records.

    When ``replies_available`` is False (report generated from persisted JSONL,
    which stores hashes not raw replies), the LLM RESPONSE QUALITY FLAGS section
    is replaced with an explanatory note and the LLM call/error pipeline-health
    lines read ``n/a`` instead of a misleading ``0``.
    """
    lines: list[str] = [
        "=== SASKI INTERNAL FINDINGS ===",
        f"Session: {run_id}",
        f"Provider: {provider}",
        f"Generated: {generated_utc}",
        "For internal use only — do not share with customers.",
        "===============================",
        "",
    ]

    per_turn_flags: dict[int, list[str]] = {}
    if replies_available:
        for rec in records:
            fired = _flags_for_turn(rec, provider)
            if fired:
                per_turn_flags[rec["index"]] = fired

    # --- LLM RESPONSE QUALITY FLAGS ---
    lines.append("--- LLM RESPONSE QUALITY FLAGS ---")
    if not replies_available:
        lines.append(_QUALITY_FLAGS_UNAVAILABLE)
        lines.append("")
    elif per_turn_flags:
        for rec in records:
            fired = per_turn_flags.get(rec["index"])
            if not fired:
                continue
            lines.append(
                f"Turn {rec['index']} [mode={rec['mode']}, "
                f"jurisdiction={rec['jurisdiction']}, domain={rec['domain_display']}]:"
            )
            lines.append(f"  Input:    {_excerpt(rec.get('redacted'), 80)}")
            lines.append(f"  LLM said: {_excerpt(rec.get('reply'), 120)}")
            lines.append(f"  Flag:     {', '.join(fired)}")
            lines.append("")
    else:
        lines.append("None detected.")
        lines.append("")

    # --- COVERAGE GAPS ---
    lines.append("--- COVERAGE GAPS ---")
    seen: set[tuple] = set()
    gap_lines: list[str] = []
    for rec in records:
        if rec.get("matched_law_ids"):
            continue
        key = (rec["jurisdiction"], str(rec["domain_display"]))
        if key in seen:
            continue
        seen.add(key)
        gap_lines.append(
            f"jurisdiction={rec['jurisdiction']}, domain={rec['domain_display']} — 0 law matches"
        )
    lines.extend(gap_lines if gap_lines else ["None detected."])
    lines.append("")

    # --- SDK CONFIGURATION SIGNALS ---
    lines.append("--- SDK CONFIGURATION SIGNALS ---")
    if sis_signals:
        for sig in sis_signals:
            sid = sig["signal_id"]
            lines.append(f"  {sid} [{sig['severity']}]: {sig['title']}")
            lines.append(
                f"  Internal action: "
                f"{_SIS_INTERNAL_ACTIONS.get(sid, 'Review signal with SASKI team.')}"
            )
            lines.append("")
    else:
        lines.append("None detected.")
        lines.append("")

    # --- PIPELINE HEALTH ---
    turns_with_pii = sum(1 for r in records if r.get("pii"))
    turns_with_distress = sum(1 for r in records if r.get("escalation"))
    total_spans = sum(int(r.get("pii_span_count", 0)) for r in records)
    avg_spans = round(total_spans / total_turns, 1) if total_turns else 0.0
    any_errors = "yes — turns " + ", ".join(str(i) for i in error_turns) if error_turns else "no"

    if replies_available:
        if provider == "none":
            llm_call_line = "0"
        else:
            llm_call_line = str(sum(1 for r in records if r.get("reply") is not None))
        llm_error_line = str(sum(1 for r in records if r.get("reply_is_error")))
    else:
        llm_call_line = "n/a (not persisted in JSONL)"
        llm_error_line = "n/a (not persisted in JSONL)"

    lines.append("--- PIPELINE HEALTH ---")
    lines.append(f"Total turns:                     {total_turns}")
    lines.append(f"Turns with PII:                  {turns_with_pii}")
    lines.append(f"Turns with distress:             {turns_with_distress}")
    lines.append(f"Turns with LLM call:             {llm_call_line}")
    lines.append(f"Turns with LLM error:            {llm_error_line}")
    lines.append(f"Avg PII spans redacted per turn: {avg_spans}")
    lines.append(f"Any turn errors:                 {any_errors}")
    lines.append("")

    # --- NOTES FOR REGISTRY OR SDK TEAM ---
    lines.append("--- NOTES FOR REGISTRY OR SDK TEAM ---")
    note_records: list[tuple[dict, str]] = []
    for rec in records:
        for ftype in per_turn_flags.get(rec["index"], []):
            if ftype in ("POSSIBLE_LAW_COMPLIANCE_GAP", "MISSING_CRISIS_LANGUAGE"):
                note_records.append((rec, ftype))
    if note_records:
        for rec, ftype in note_records:
            laws = ", ".join(rec["matched_law_ids"]) if rec.get("matched_law_ids") else "(none)"
            lines.append(
                f"Turn {rec['index']} — jurisdiction={rec['jurisdiction']}, "
                f"domain={rec['domain_display']}"
            )
            lines.append(f"  Matched laws: {laws}")
            lines.append(f"  Flag type: {ftype}")
            lines.append("  Note: LLM response did not reference applicable law context.")
            lines.append("        Review whether SDK post-LLM output scanning would catch this.")
            lines.append("")
    else:
        lines.append("None detected.")
        lines.append("")

    lines.append("===============================")
    lines.append("End of internal findings.")
    return "\n".join(lines) + "\n"
