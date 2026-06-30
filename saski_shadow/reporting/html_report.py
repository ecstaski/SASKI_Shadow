"""Render a shadow_report_v1 dict into a self-contained HTML document.

Design constraints (see docs/CUSTOMER_REPORT_STANDARDS.md):
  * Observation-only language throughout. Shadow observed traffic; it did not
    block, modify, or suppress any LLM output. No enforcement is claimed.
  * Self-contained: inline CSS only, no external fonts/scripts/images.
  * Zero runtime dependencies: standard library only.
  * Branded "SASKI Institute PBC" consistently.
"""

from __future__ import annotations

from html import escape
from typing import Any

BRAND = "SASKI Institute PBC"
CONTACT_LINE = "Contact SASKI Institute PBC \u00b7 info@techviz.us \u00b7 www.techviz.us"
FOOTER_LINE = (
    "\u00a9 2026 SASKI Institute PBC \u00b7 Baseline shadow observation report "
    "\u00b7 Not clinical-grade \u00b7 info@techviz.us"
)
OBSERVATION_BANNER = (
    "Observation-only report. In shadow mode SASKI observed this traffic; it did "
    "not block, modify, or suppress any LLM output. Absence of a finding is not "
    "evidence of compliance."
)

# Color palette (documented in CUSTOMER_REPORT_STANDARDS.md).
_CSS = """
:root {
  --navy: #1f2a44;
  --teal: #2f6f6b;
  --bg: #f5f7fa;
  --card: #ffffff;
  --border: #e2e6ec;
  --text: #1f2430;
  --muted: #5b6472;
  --sev-action: #b23b3b;
  --sev-warning: #b9851f;
  --sev-info: #2f6f6b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  font-size: 15px;
  line-height: 1.55;
}
.page { max-width: 980px; margin: 0 auto; padding: 32px 24px 64px; }
.cover {
  background: linear-gradient(135deg, var(--navy), #2b3a5e);
  color: #fff;
  border-radius: 14px;
  padding: 40px 36px;
  margin-bottom: 28px;
}
.cover h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: -0.01em; }
.cover .sub { font-size: 15px; opacity: 0.85; margin-bottom: 24px; }
.cover .meta { display: grid; grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 12px 28px; font-size: 14px; }
.cover .meta b { display: block; opacity: 0.7; font-weight: 600; font-size: 12px;
  text-transform: uppercase; letter-spacing: 0.04em; }
.banner {
  background: #fff7ed;
  border: 1px solid #f0d9b5;
  border-left: 4px solid var(--sev-warning);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 28px;
  font-size: 13.5px;
  color: #5a4a25;
}
section.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px 26px;
  margin-bottom: 22px;
}
section.card > h2 {
  margin: 0 0 4px;
  font-size: 19px;
  color: var(--navy);
}
section.card > .lead { color: var(--muted); margin: 0 0 16px; font-size: 13.5px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr));
  gap: 14px; margin: 4px 0 14px; }
.stat { background: var(--bg); border: 1px solid var(--border); border-radius: 9px;
  padding: 12px 14px; }
.stat .n { font-size: 22px; font-weight: 700; color: var(--navy); }
.stat .l { font-size: 12px; color: var(--muted); text-transform: uppercase;
  letter-spacing: 0.03em; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 13.5px; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border);
  vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.03em; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.note { background: var(--bg); border-radius: 8px; padding: 11px 14px; font-size: 12.5px;
  color: var(--muted); margin: 10px 0; }
.disclaimer { font-size: 12px; color: var(--muted); font-style: italic; margin-top: 12px; }
.law { border: 1px solid var(--border); border-radius: 8px; padding: 10px 13px;
  margin: 8px 0; }
.law .id { font-weight: 700; color: var(--navy); }
.law .cite { font-size: 12.5px; color: var(--muted); }
.pill { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 9px;
  border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em; }
.pill.future { background: #eef3ff; color: #33518f; }
.pill.inforce { background: #e9f4ec; color: #2c6b41; }
.signal { border: 1px solid var(--border); border-left-width: 4px; border-radius: 8px;
  padding: 13px 16px; margin: 10px 0; }
.signal.action_required { border-left-color: var(--sev-action); }
.signal.warning { border-left-color: var(--sev-warning); }
.signal.info { border-left-color: var(--sev-info); }
.signal .head { display: flex; justify-content: space-between; align-items: baseline;
  gap: 12px; }
.signal .sid { font-weight: 700; color: var(--navy); }
.signal .sev { font-size: 11px; font-weight: 700; text-transform: uppercase; }
.signal.action_required .sev { color: var(--sev-action); }
.signal.warning .sev { color: var(--sev-warning); }
.signal.info .sev { color: var(--sev-info); }
.signal p { margin: 7px 0 0; font-size: 13.5px; }
.signal .label { color: var(--muted); font-weight: 600; font-size: 12px; }
.empty { color: var(--muted); font-style: italic; }
.coverage {
  background: #eef3ff;
  border: 1px solid #cfdcf7;
  border-left: 4px solid #33518f;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 28px;
  font-size: 13.5px;
  color: #2a3a5e;
}
.coverage b { display: block; margin-bottom: 4px; }
.coverage ul { margin: 6px 0 0; padding-left: 20px; }
.coverage li { margin: 3px 0; }
footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 30px;
  padding-top: 18px; border-top: 1px solid var(--border); }
footer .contact { color: var(--navy); font-weight: 600; margin-bottom: 4px; }
"""


# --- small helpers ----------------------------------------------------------

def _esc(value: Any) -> str:
    return escape("" if value is None else str(value))


def _fmt_num(value: Any) -> str:
    if value is None:
        return "\u2014"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return _esc(value)


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "\u2014"
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return _esc(value)


def _fmt_pct_value(value: Any) -> str:
    """Format a value that is *already* a percentage (e.g. 12.5 -> '12.5%')."""
    if value is None:
        return "\u2014"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return _esc(value)


def _stat(n: Any, label: str, *, is_pct: bool = False, pct_value: bool = False) -> str:
    if pct_value:
        shown = _fmt_pct_value(n)
    elif is_pct:
        shown = _fmt_pct(n)
    else:
        shown = _fmt_num(n)
    return f'<div class="stat"><div class="n">{shown}</div><div class="l">{_esc(label)}</div></div>'


def _first_session_id(report: dict[str, Any]) -> str | None:
    sections = report.get("sections", {})
    for key in ("envelope_evidence_sample", "pii_phi_detection_summary",
                "escalation_signal_count", "compliance_exposure_examples"):
        section = sections.get(key, {})
        for bucket in ("samples", "examples"):
            for item in section.get(bucket, []) or []:
                sid = item.get("session_id")
                if sid:
                    return str(sid)
    return None


# --- section renderers ------------------------------------------------------

def _cover(report: dict[str, Any]) -> str:
    methodology = report.get("methodology", {})
    period = report.get("period", {})
    session_id = _first_session_id(report) or "n/a"
    meta_rows = [
        ("Session ID", session_id),
        ("Generated (UTC)", report.get("generated_at_utc")),
        ("Reporting period", f'{period.get("start_utc") or "n/a"} \u2192 '
         f'{period.get("end_utc") or "n/a"}'),
        ("Law set version", methodology.get("law_set_version")),
        ("Laws evaluated", methodology.get("total_laws_evaluated")),
        ("Jurisdictions", methodology.get("total_jurisdictions")),
    ]
    meta_html = "".join(
        f"<div><b>{_esc(label)}</b>{_esc(value)}</div>" for label, value in meta_rows
    )
    return (
        '<div class="cover">'
        "<h1>SASKI Shadow Pilot Report</h1>"
        '<div class="sub">Baseline AI safety &amp; compliance observation '
        f'\u00b7 {_esc(BRAND)}</div>'
        f'<div class="meta">{meta_html}</div>'
        "</div>"
    )


def _coverage_banner(report: dict[str, Any]) -> str:
    """Render the run's coverage notice so empty sections are never misread.

    Distinguishes "evaluated and clear" from "not evaluated this run" by naming
    the capabilities that received no inputs. Renders nothing if the report
    carries no coverage notice.
    """
    notice = report.get("coverage_notice")
    if not isinstance(notice, dict):
        return ""
    inactive = notice.get("inactive_capabilities") or []
    if not inactive:
        return (
            '<div class="coverage"><b>Run coverage</b>'
            "All observable baseline capabilities were exercised in this run. "
            "Empty sections below mean nothing was observed, not that a check was "
            "skipped.</div>"
        )
    items = "".join(f"<li>{_esc(item)}</li>" for item in inactive)
    return (
        '<div class="coverage"><b>What was not measured in this run</b>'
        "The following baseline capabilities produced no signal because their "
        "inputs were not supplied. An empty or zero result for these is "
        '"not evaluated", not "nothing found":'
        f"<ul>{items}</ul></div>"
    )


def _section_open(title: str, lead: str) -> str:
    return f'<section class="card"><h2>{_esc(title)}</h2><p class="lead">{_esc(lead)}</p>'


def _render_pii(s: dict[str, Any]) -> str:
    totals = s.get("totals", {})
    html = _section_open(
        "1. PII / PHI Detection Summary",
        "Personal-data signals observed by baseline regex detectors. Counts are "
        "observations only.",
    )
    html += '<div class="stat-grid">'
    html += _stat(totals.get("turns_processed"), "Turns processed")
    html += _stat(totals.get("turns_with_pii"), "Turns with PII")
    html += _stat(totals.get("pii_detection_rate"), "Detection rate", is_pct=True)
    html += "</div>"

    by_type = {k: v for k, v in (s.get("by_pii_type") or {}).items() if v}
    if by_type:
        rows = "".join(
            f"<tr><td>{_esc(k)}</td><td class='num'>{_fmt_num(v)}</td></tr>"
            for k, v in sorted(by_type.items(), key=lambda kv: -kv[1])
        )
        html += f"<table><tr><th>PII type</th><th class='num'>Count</th></tr>{rows}</table>"
    else:
        html += '<p class="empty">No PII types observed in this session.</p>'

    if s.get("baseline_only_caveat"):
        html += f'<div class="note">{_esc(s["baseline_only_caveat"])}</div>'
    return html + "</section>"


def _law_domain_label(law: dict[str, Any]) -> str:
    """Resolve a law's domain tag for display (``domains`` list or legacy ``domain``)."""
    domains = law.get("domains")
    if isinstance(domains, list) and domains:
        return ", ".join(str(d) for d in domains)
    value = law.get("domain")
    return str(value) if value else ""


def _render_compliance(s: dict[str, Any]) -> str:
    summary = s.get("law_match_summary", {})
    by_status = s.get("matched_laws_by_status", {})
    html = _section_open(
        "2. Compliance Exposure Examples",
        "Named laws matched on integrator-supplied jurisdiction and domain "
        "metadata. Surfaced for awareness; no enforcement was applied.",
    )
    html += '<div class="stat-grid">'
    html += _stat(summary.get("turns_with_jurisdiction_metadata"), "Turns w/ metadata")
    html += _stat(summary.get("turns_with_law_match"), "Turns w/ law match")
    html += _stat(summary.get("future_effective_count"), "Future-effective laws")
    html += "</div>"

    def _laws(laws: list, css: str, label: str) -> str:
        if not laws:
            return ""
        out = ""
        for law in laws:
            out += (
                '<div class="law">'
                f'<span class="pill {css}">{_esc(label)}</span> '
                f'<span class="id">{_esc(law.get("law_id"))}</span> '
                f'<span class="cite">\u2014 {_esc(law.get("jurisdiction"))} / '
                f'{_esc(_law_domain_label(law))}</span>'
                f'<div class="cite">{_esc(law.get("citation"))}</div>'
                "</div>"
            )
        return out

    laws_html = _laws(by_status.get("in_force", []), "inforce", "in force")
    laws_html += _laws(by_status.get("future_effective", []), "future", "future")
    if laws_html:
        html += laws_html
    else:
        statement = summary.get("no_match_statement") or "No laws matched this session."
        html += f'<p class="empty">{_esc(statement)}</p>'

    for limitation in s.get("detection_limitations", []) or []:
        html += f'<div class="note">{_esc(limitation)}</div>'
    if s.get("disclaimer"):
        html += f'<p class="disclaimer">{_esc(s["disclaimer"])}</p>'
    return html + "</section>"


def _render_token_savings(s: dict[str, Any]) -> str:
    measured = s.get("measured_from_shadow", {})
    savings = s.get("savings", {})
    model = s.get("token_model", {})
    inputs = s.get("prospect_inputs", {})
    html = _section_open(
        "3. Token Savings Calculation",
        "Estimate computed by transparent arithmetic from two integrator inputs "
        "applied to observed governance tiers. Dollar figures are never computed.",
    )
    html += f'<div class="note">Basis: <b>{_esc(s.get("basis"))}</b></div>'

    html += '<div class="stat-grid">'
    html += _stat(measured.get("total_turns"), "Total turns")
    html += _stat(measured.get("tier_clean_turns"), "Tier 1 (clean)")
    html += _stat(measured.get("tier_warning_turns"), "Tier 2 (warning)")
    html += _stat(measured.get("tier_escalation_turns"), "Tier 3 (escalation)")
    html += _stat(measured.get("regulated_mode_turns"), "Regulated-mode turns")
    html += "</div>"

    rows = [
        ("Legacy system prompt tokens (input)", inputs.get("legacy_system_prompt_tokens")),
        ("Lean product prompt tokens (input)", inputs.get("lean_product_prompt_tokens")),
        ("Regulated-mode floor tokens", model.get("regulated_mode_floor_tokens")),
        ("Warning append tokens", model.get("warning_append_tokens")),
        ("Tier 3 LLM tokens (enforce mode)", model.get("tier3_llm_tokens")),
        ("Tokens saved \u2014 Tier 1", savings.get("tier_clean_tokens_saved")),
        ("Tokens saved \u2014 Tier 2", savings.get("tier_warning_tokens_saved")),
        ("Tokens saved \u2014 Tier 3", savings.get("tier_escalation_tokens_saved")),
    ]
    rows_html = "".join(
        f"<tr><td>{_esc(label)}</td><td class='num'>{_fmt_num(value)}</td></tr>"
        for label, value in rows
    )
    total_saved = savings.get("tokens_saved_estimate")
    rows_html += (
        f"<tr><td><b>Total tokens saved (estimate)</b></td>"
        f"<td class='num'><b>{_fmt_num(total_saved)}</b></td></tr>"
    )
    html += f"<table><tr><th>Line item</th><th class='num'>Tokens</th></tr>{rows_html}</table>"

    if s.get("dollar_savings_note"):
        html += f'<div class="note">{_esc(s["dollar_savings_note"])}</div>'
    if measured.get("shadow_mode_note"):
        html += f'<div class="note">{_esc(measured["shadow_mode_note"])}</div>'
    if s.get("disclaimer"):
        html += f'<p class="disclaimer">{_esc(s["disclaimer"])}</p>'
    return html + "</section>"


def _render_envelope(s: dict[str, Any]) -> str:
    samples = s.get("samples", []) or []
    html = _section_open(
        "4. Envelope Evidence Sample",
        "Representative transport envelopes captured during observation (hashed, "
        "no message contents).",
    )
    if not samples:
        html += '<p class="empty">No envelope samples captured.</p>'
        return html + "</section>"
    rows = ""
    for sample in samples:
        transport = sample.get("transport_audit_record", {}) or {}
        pii_types = ", ".join(transport.get("pii_types", []) or []) or "\u2014"
        rows += (
            f"<tr><td class='num'>{_esc(sample.get('turn_index'))}</td>"
            f"<td>{_esc(sample.get('session_id'))}</td>"
            f"<td>{_esc(sample.get('mode_tag'))}</td>"
            f"<td>{_esc(pii_types)}</td>"
            f"<td>{_fmt_num(transport.get('redaction_applied'))}</td></tr>"
        )
    html += (
        "<table><tr><th class='num'>Turn</th><th>Session</th><th>Mode tag</th>"
        f"<th>PII types</th><th>Redaction applied</th></tr>{rows}</table>"
    )
    return html + "</section>"


def _render_escalation(s: dict[str, Any]) -> str:
    totals = s.get("totals", {})
    html = _section_open(
        "5. Escalation Signal Count",
        "Baseline distress phrase-list matches. Not clinical crisis detection.",
    )
    html += '<div class="stat-grid">'
    html += _stat(totals.get("turns_processed"), "Turns processed")
    html += _stat(totals.get("escalation_turns"), "Escalation signals")
    html += _stat(totals.get("escalation_rate"), "Escalation rate", is_pct=True)
    html += "</div>"

    by_tier = {k: v for k, v in (s.get("by_governance_tier") or {}).items() if v}
    if by_tier:
        rows = "".join(
            f"<tr><td>{_esc(k)}</td><td class='num'>{_fmt_num(v)}</td></tr>"
            for k, v in by_tier.items()
        )
        html += f"<table><tr><th>Governance tier</th><th class='num'>Turns</th></tr>{rows}</table>"

    if s.get("baseline_only_caveat"):
        html += f'<div class="note">{_esc(s["baseline_only_caveat"])}</div>'
    if s.get("disclaimer"):
        html += f'<p class="disclaimer">{_esc(s["disclaimer"])}</p>'
    return html + "</section>"


def _render_unsafe_flows(s: dict[str, Any]) -> str:
    categories = s.get("categories", {}) or {}
    html = _section_open(
        "6. Unsafe Flow Documentation",
        "Turns where enforce mode would have taken a different path. In shadow "
        "mode these flows were observed only \u2014 no action was taken.",
    )
    nonempty = {k: v for k, v in categories.items() if v}
    if not nonempty:
        html += '<p class="empty">No unsafe flows observed in this session.</p>'
        return html + "</section>"
    rows = "".join(
        f"<tr><td>{_esc(name)}</td><td class='num'>{_fmt_num(len(items))}</td></tr>"
        for name, items in nonempty.items()
    )
    html += (
        "<table><tr><th>Category</th><th class='num'>Turns observed</th></tr>"
        f"{rows}</table>"
    )
    return html + "</section>"


def _render_latency(s: dict[str, Any]) -> str:
    agg = s.get("aggregate", {})
    html = _section_open(
        "7. Latency Impact Report",
        "Per-turn pipeline latency observed during the run.",
    )
    html += '<div class="stat-grid">'
    html += _stat(agg.get("turn_count"), "Turns timed")
    html += _stat(agg.get("p50_total_ms"), "p50 (ms)")
    html += _stat(agg.get("p95_total_ms"), "p95 (ms)")
    html += _stat(agg.get("p99_total_ms"), "p99 (ms)")
    html += "</div>"

    phases = s.get("phase_timings", {}) or {}
    if phases:
        rows = "".join(
            f"<tr><td>{_esc(phase)}</td>"
            f"<td class='num'>{_fmt_num(v.get('p50'))}</td>"
            f"<td class='num'>{_fmt_num(v.get('p95'))}</td>"
            f"<td class='num'>{_fmt_num(v.get('p99'))}</td></tr>"
            for phase, v in phases.items()
        )
        html += (
            "<table><tr><th>Phase</th><th class='num'>p50</th><th class='num'>p95</th>"
            f"<th class='num'>p99</th></tr>{rows}</table>"
        )
    return html + "</section>"


def _render_recommended_path(s: dict[str, Any]) -> str:
    findings = s.get("findings_summary", {})
    dist = s.get("expected_production_tier_distribution", {})
    html = _section_open(
        "8. Recommended Path",
        "Observed-traffic summary to inform an integrator's rollout planning.",
    )
    html += '<div class="stat-grid">'
    html += _stat(dist.get("tier_clean_pct"), "Tier 1 (clean)", pct_value=True)
    html += _stat(dist.get("tier_warning_pct"), "Tier 2 (warning)", pct_value=True)
    html += _stat(dist.get("tier_escalation_pct"), "Tier 3 (escalation)", pct_value=True)
    html += "</div>"
    rows = [
        ("PII risk", findings.get("pii_risk")),
        ("Escalation signal rate", findings.get("escalation_signal_rate")),
        ("Latency acceptable", findings.get("latency_acceptable")),
    ]
    rows_html = "".join(
        f"<tr><td>{_esc(label)}</td><td>{_fmt_num(value)}</td></tr>"
        for label, value in rows
    )
    html += f"<table><tr><th>Finding</th><th>Observed</th></tr>{rows_html}</table>"
    steps = s.get("next_steps", []) or []
    if steps:
        items = "".join(f"<li>{_esc(step)}</li>" for step in steps)
        html += f"<ul>{items}</ul>"
    return html + "</section>"


def _render_sdk_signals(s: dict[str, Any]) -> str:
    signals = s.get("signals", []) or []
    html = _section_open(
        "9. SDK Integration Signals",
        _esc(s.get("summary") or "Integration signals derived from this session."),
    )
    if not signals:
        html += '<p class="empty">No integration signals detected for this session.</p>'
        return html + "</section>"
    for sig in signals:
        sev = sig.get("severity", "info")
        sev_class = sev if sev in ("action_required", "warning", "info") else "info"
        html += (
            f'<div class="signal {sev_class}">'
            '<div class="head">'
            f'<span class="sid">{_esc(sig.get("signal_id"))} \u00b7 {_esc(sig.get("title"))}</span>'
            f'<span class="sev">{_esc(sev.replace("_", " "))}</span>'
            "</div>"
            f'<p><span class="label">Observation:</span> {_esc(sig.get("observation"))}</p>'
            f'<p><span class="label">SDK guidance:</span> {_esc(sig.get("sdk_recommendation"))}</p>'
            "</div>"
        )
    return html + "</section>"


_RENDERERS = [
    ("pii_phi_detection_summary", _render_pii),
    ("compliance_exposure_examples", _render_compliance),
    ("token_savings_calculation", _render_token_savings),
    ("envelope_evidence_sample", _render_envelope),
    ("escalation_signal_count", _render_escalation),
    ("unsafe_flow_documentation", _render_unsafe_flows),
    ("latency_impact_report", _render_latency),
    ("recommended_path", _render_recommended_path),
    ("sdk_integration_signals", _render_sdk_signals),
]


def render_html_report(report: dict[str, Any]) -> str:
    """Return a complete, self-contained HTML document for a shadow report."""
    sections = report.get("sections", {})
    body = [_cover(report), f'<div class="banner">{_esc(OBSERVATION_BANNER)}</div>']
    coverage_banner = _coverage_banner(report)
    if coverage_banner:
        body.append(coverage_banner)
    for key, renderer in _RENDERERS:
        section = sections.get(key)
        if isinstance(section, dict):
            body.append(renderer(section))
    body.append(
        "<footer>"
        f'<div class="contact">{_esc(CONTACT_LINE)}</div>'
        f"<div>{_esc(FOOTER_LINE)}</div>"
        "</footer>"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>SASKI Shadow Pilot Report</title>"
        f"<style>{_CSS}</style></head><body>"
        f'<div class="page">{"".join(body)}</div>'
        "</body></html>\n"
    )


def generate_html_report(report: dict[str, Any], output_path: str) -> str:
    """Render ``report`` to HTML and write it to ``output_path``.

    Returns the HTML string that was written.
    """
    html = render_html_report(report)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(html)
    return html
