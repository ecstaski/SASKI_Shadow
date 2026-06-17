"""Shadow pilot report aggregation.

Reads persisted hash-only turn payloads (JSONL) and produces a
``shadow_report_v1`` document with eight sections. All analysis has already
happened upstream; this module only counts, samples, and presents.

The aggregator reads the pre-computed ``governance_tier`` from each turn's
``engine_summary`` and defaults to ``tier_clean`` when it is absent. It never
re-derives tier classification. Report vocabulary uses ``PublicOutcome``
values only; no engine action strings appear in the output.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

from ..enums import PublicOutcome
from ..laws import match_laws

# Required messaging strings.
COMPLIANCE_DISCLAIMER = (
    "This report reflects a starter set of laws and will expand as coverage "
    "grows. It does not apply private SASKI enforcement mappings, thresholds, "
    "or internal policy logic."
)
UPGRADE_MESSAGE = (
    "For comprehensive results, add the licensed SASKI engine to your VPC deployment."
)
ESCALATION_DISCLAIMER = (
    "Escalation counts reflect baseline distress phrase-list matches only and are "
    "not clinical crisis detection."
)

_MAX_EXAMPLES = 10
_PII_BUCKETS = (
    "ssn",
    "phone",
    "email",
    "name",
    "date_of_birth",
    "insurance_id",
    "address",
    "credit_card",
)
_OUTCOME_KEYS = [o.value for o in PublicOutcome]
_RISK_BANDS = ("low", "moderate", "elevated", "critical")
_TIERS = ("tier_clean", "tier_warning", "tier_escalation")


def load_turns_jsonl(path: str) -> list[dict[str, Any]]:
    """Load one JSON object per line from integrator turn store."""
    turns: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            turns.append(json.loads(line))
    return turns


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _engine_summary(turn: dict[str, Any]) -> dict[str, Any]:
    summary = turn.get("engine_summary")
    return summary if isinstance(summary, dict) else {}


def _governance_tier(turn: dict[str, Any]) -> str:
    tier = _engine_summary(turn).get("governance_tier")
    return tier if tier in _TIERS else "tier_clean"


def _pii_types(turn: dict[str, Any]) -> list[str]:
    summary = _engine_summary(turn)
    types = summary.get("pii_types")
    if not types:
        transport = turn.get("transport_audit_record") or {}
        types = transport.get("pii_types")
    return [str(t) for t in types] if isinstance(types, list) else []


def _bucket(pii_type: str) -> str:
    return pii_type if pii_type in _PII_BUCKETS else "other"


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (rank - low))


def _section_pii(turns: list[dict[str, Any]], period: dict[str, Any]) -> dict[str, Any]:
    by_type = {key: 0 for key in (*_PII_BUCKETS, "other")}
    turns_with_pii = 0
    aggregate_types: set[str] = set()
    examples: list[dict[str, Any]] = []

    for turn in turns:
        summary = _engine_summary(turn)
        types = _pii_types(turn)
        if summary.get("pii_detected") or types:
            turns_with_pii += 1
            for ptype in types:
                by_type[_bucket(ptype)] += 1
                aggregate_types.add(ptype)
            if len(examples) < _MAX_EXAMPLES:
                transport = turn.get("transport_audit_record") or {}
                examples.append(
                    {
                        "turn_index": turn.get("turn_index", 0),
                        "session_id": turn.get("session_id", ""),
                        "pii_types": types,
                        "input_hash": turn.get("input_hash"),
                        "redaction_applied": bool(transport.get("redaction_applied", bool(types))),
                        "message_for_llm_hash": transport.get("message_for_llm_hash"),
                    }
                )

    total = len(turns)
    return {
        "section": "pii_phi_detection_summary",
        "period": dict(period),
        "totals": {
            "turns_processed": total,
            "turns_with_pii": turns_with_pii,
            "pii_detection_rate": (turns_with_pii / total) if total else 0.0,
        },
        "by_pii_type": by_type,
        "history_redaction": {
            "sessions_with_history_pii": 0,
            "aggregate_pii_types_found": sorted(aggregate_types),
        },
        "examples": examples,
    }


def _compliance_decisions(turn: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = turn.get("compliance_decisions")
    if isinstance(decisions, list):
        return [d for d in decisions if isinstance(d, dict)]
    return []


def _turn_jurisdiction(turn: dict[str, Any], prospect_inputs: dict[str, Any]) -> str | None:
    # Precedence: explicit per-turn field, then engine_summary passthrough,
    # then a single report-level fallback supplied by the integrator.
    value = turn.get("jurisdiction") or _engine_summary(turn).get("user_jurisdiction")
    if not value:
        value = prospect_inputs.get("user_jurisdiction")
    return str(value) if value else None


def _turn_domain(turn: dict[str, Any], prospect_inputs: dict[str, Any]) -> str | None:
    value = turn.get("domain") or _engine_summary(turn).get("domain")
    if not value:
        value = prospect_inputs.get("domain")
    return str(value) if value else None


def _section_compliance(turns: list[dict[str, Any]], prospect_inputs: dict[str, Any]) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    reason_codes: set[str] = set()
    turns_with_compliance = 0
    turns_with_jurisdiction = 0
    user_jurisdiction_injected = False

    turns_with_jurisdiction_metadata = 0
    turns_with_law_match = 0
    matched_laws_by_id: dict[str, dict[str, str]] = {}

    for turn in turns:
        summary = _engine_summary(turn)
        decisions = _compliance_decisions(turn)
        transport = turn.get("transport_audit_record") or {}
        jurisdiction_source = transport.get("jurisdiction_source")
        if jurisdiction_source == "integrator_supplied":
            turns_with_jurisdiction += 1
            user_jurisdiction_injected = True

        # Named-law matching is keyed purely on integrator-supplied jurisdiction
        # and domain. Signals are attached below as display context only; they
        # never gate which law matches.
        jurisdiction = _turn_jurisdiction(turn, prospect_inputs)
        domain = _turn_domain(turn, prospect_inputs)
        if jurisdiction and domain:
            turns_with_jurisdiction_metadata += 1
        matched = match_laws(jurisdiction, domain)
        if matched:
            turns_with_law_match += 1
            for law in matched:
                matched_laws_by_id[law["law_id"]] = law

        if decisions:
            turns_with_compliance += 1
            for decision in decisions:
                code = decision.get("reason_code")
                if code:
                    reason_codes.add(str(code))

        if (decisions or matched) and len(examples) < _MAX_EXAMPLES:
            deployment = turn.get("deployment_decision") or {}
            would_block = bool(summary.get("would_block"))
            examples.append(
                {
                    "turn_index": turn.get("turn_index", 0),
                    "session_id": turn.get("session_id", ""),
                    "deployment_profile": prospect_inputs.get("deployment_profile"),
                    "user_jurisdiction": jurisdiction,
                    "domain": domain,
                    "jurisdiction_source": jurisdiction_source,
                    "obligation_label": decisions[0].get("obligation_label") if decisions else None,
                    "reason_code": decisions[0].get("reason_code") if decisions else None,
                    "compliance_decisions": {
                        str(d.get("rule_id", f"rule_{i}")): {
                            "action": d.get("action"),
                            "reason_code": d.get("reason_code"),
                        }
                        for i, d in enumerate(decisions)
                    },
                    "matched_laws": matched,
                    "observed_signals": {
                        "pii_detected": bool(summary.get("pii_detected")),
                        "pii_types": list(summary.get("pii_types") or []),
                        "escalation_detected": bool(summary.get("escalation_detected")),
                        "outcome": summary.get("outcome") if summary.get("outcome") in _OUTCOME_KEYS else None,
                    },
                    "engine_outcome": summary.get("outcome"),
                    "would_have_blocked_in_enforce": would_block,
                    "enforcement_suppressed_in_shadow": bool(
                        deployment.get("enforcement_suppressed", would_block)
                    ),
                }
            )

    matched_laws = [matched_laws_by_id[k] for k in sorted(matched_laws_by_id)]
    if matched_laws:
        no_match_statement = None
    elif turns_with_jurisdiction_metadata == 0:
        no_match_statement = (
            "No jurisdiction/domain metadata was supplied on any turn, so no laws were matched."
        )
    else:
        no_match_statement = (
            "No laws in the starter set matched the supplied jurisdiction/domain metadata."
        )

    active = prospect_inputs.get("active_jurisdictions") or []
    return {
        "section": "compliance_exposure_examples",
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "upgrade_path": UPGRADE_MESSAGE,
        "jurisdiction_config": {
            "active_jurisdictions": list(active),
            "user_jurisdiction_injected": user_jurisdiction_injected,
        },
        "examples": examples,
        "matched_laws": matched_laws,
        "law_match_summary": {
            "turns_with_jurisdiction_metadata": turns_with_jurisdiction_metadata,
            "turns_with_law_match": turns_with_law_match,
            "unique_law_ids": [law["law_id"] for law in matched_laws],
            "no_match_statement": no_match_statement,
        },
        "aggregate": {
            "turns_with_compliance_decisions": turns_with_compliance,
            "turns_with_jurisdiction_decision": turns_with_jurisdiction,
            "unique_reason_codes": sorted(reason_codes),
        },
    }


def _section_token_savings(
    turns: list[dict[str, Any]],
    prospect_inputs: dict[str, Any],
) -> dict[str, Any]:
    tier_counts = {tier: 0 for tier in _TIERS}
    blocked = 0
    for turn in turns:
        tier_counts[_governance_tier(turn)] += 1
        summary = _engine_summary(turn)
        if summary.get("would_block") or summary.get("outcome") == PublicOutcome.BLOCK.value:
            blocked += 1

    return {
        "section": "token_savings_calculation",
        "upgrade_path": UPGRADE_MESSAGE,
        "prospect_inputs": {
            "avg_tokens_per_session_legacy_system": prospect_inputs.get(
                "avg_tokens_per_session_legacy_system"
            ),
            "avg_llm_turns_per_session": prospect_inputs.get("avg_llm_turns_per_session"),
            "monthly_sessions": prospect_inputs.get("monthly_sessions"),
            "input_price_per_1m_tokens_usd": prospect_inputs.get("input_price_per_1m_tokens_usd"),
        },
        "measured_from_shadow": {
            "total_turns": len(turns),
            "tier_clean_turns": tier_counts["tier_clean"],
            "tier_warning_turns": tier_counts["tier_warning"],
            "tier_escalation_turns": tier_counts["tier_escalation"],
            "blocked_llm_turns": blocked,
        },
        "token_model": {
            "legacy_system_tokens_per_turn": None,
            "governed_system_tokens_per_turn": None,
            "warning_append_tokens": None,
            "regulated_floor_tokens": None,
        },
        "savings": {
            "tokens_saved_per_session_estimate": None,
            "monthly_tokens_saved_estimate": None,
            "annual_usd_saved_estimate": None,
        },
    }


def _section_envelope_sample(turns: list[dict[str, Any]]) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for turn in turns:
        if len(samples) >= _MAX_EXAMPLES:
            break
        samples.append(
            {
                "turn_index": turn.get("turn_index", 0),
                "session_id": turn.get("session_id", ""),
                "mode_tag": turn.get("mode_tag", "shadow_mode"),
                "envelope": turn.get("envelope") or {},
                "transport_audit_record": turn.get("transport_audit_record") or {},
            }
        )
    return {"section": "envelope_evidence_sample", "samples": samples}


def _section_escalation(turns: list[dict[str, Any]]) -> dict[str, Any]:
    by_tier = {tier: 0 for tier in _TIERS}
    by_outcome = {key: 0 for key in _OUTCOME_KEYS}
    by_risk = {band: 0 for band in _RISK_BANDS}
    escalation_turns = 0
    examples: list[dict[str, Any]] = []

    for turn in turns:
        summary = _engine_summary(turn)
        by_tier[_governance_tier(turn)] += 1
        outcome = summary.get("outcome")
        if outcome in by_outcome:
            by_outcome[outcome] += 1
        risk = summary.get("risk_band")
        if risk in by_risk:
            by_risk[risk] += 1
        if summary.get("escalation_detected"):
            escalation_turns += 1
            if len(examples) < _MAX_EXAMPLES:
                examples.append(
                    {
                        "turn_index": turn.get("turn_index", 0),
                        "session_id": turn.get("session_id", ""),
                        "escalation_detected": True,
                        "outcome": outcome if outcome in by_outcome else None,
                        "risk_band": risk if risk in by_risk else None,
                        "input_hash": turn.get("input_hash"),
                        "llm_egress_suppressed": bool(summary.get("would_block")),
                        "shadow_actual_llm_response_hash": turn.get("output_hash")
                        or turn.get("response_hash"),
                    }
                )

    total = len(turns)
    return {
        "section": "escalation_signal_count",
        "disclaimer": ESCALATION_DISCLAIMER,
        "upgrade_path": UPGRADE_MESSAGE,
        "totals": {
            "turns_processed": total,
            "escalation_turns": escalation_turns,
            "escalation_rate": (escalation_turns / total) if total else 0.0,
        },
        "by_governance_tier": by_tier,
        "by_outcome": by_outcome,
        "by_risk_band": by_risk,
        "examples": examples,
    }


def _section_unsafe_flows(turns: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = {
        "enforcement_would_block": [],
        "policy_boundary_failure": [],
        "content_sanitization_gap": [],
        "integrator_override": [],
        "manual_review_required": [],
        "other": [],
    }
    examples: list[dict[str, Any]] = []

    def _record(turn: dict[str, Any], category: str, recommended: str) -> None:
        summary = _engine_summary(turn)
        deployment = turn.get("deployment_decision") or {}
        outcome = summary.get("outcome")
        finding = {
            "turn_index": turn.get("turn_index", 0),
            "session_id": turn.get("session_id", ""),
            "category": category,
            "signals": {
                "enforcement_suppressed": bool(deployment.get("enforcement_suppressed")),
                "would_block": bool(summary.get("would_block")),
                "outcome": outcome if outcome in _OUTCOME_KEYS else None,
                "human_review_required": outcome == PublicOutcome.HUMAN_REVIEW.value,
            },
            "recommended_behavior": recommended,
            "observed_llm_response_hash": turn.get("output_hash") or turn.get("response_hash"),
            "analyst_note": "",
        }
        categories[category].append(finding)
        if len(examples) < _MAX_EXAMPLES:
            examples.append(finding)

    for turn in turns:
        summary = _engine_summary(turn)
        outcome = summary.get("outcome")
        review = turn.get("output_review") or {}

        if summary.get("would_block"):
            _record(turn, "enforcement_would_block", "Block LLM egress; serve governed template")
        elif outcome == PublicOutcome.HUMAN_REVIEW.value:
            _record(turn, "manual_review_required", "Route turn to a human reviewer")

        if review.get("pii_leaked_types"):
            _record(turn, "content_sanitization_gap", "Re-run output sanitization before egress")
        if review.get("policy_boundary_hits"):
            _record(turn, "policy_boundary_failure", "Review integrator policy boundary handling")

    return {
        "section": "unsafe_flow_documentation",
        "categories": categories,
        "examples": examples,
    }


def _section_latency(
    turns: list[dict[str, Any]],
    latency_targets: dict[str, float],
) -> dict[str, Any]:
    integrator_target = latency_targets.get("integrator_p95_target_ms")
    hosted_target = latency_targets.get("hosted_p95_target_ms")

    totals: list[float] = []
    phase_values: dict[str, list[float]] = {}
    exceeded_integrator = 0
    exceeded_hosted = 0
    outliers: list[dict[str, Any]] = []

    for turn in turns:
        latency = turn.get("latency_ms")
        if isinstance(latency, (int, float)):
            latency = float(latency)
            totals.append(latency)
            if integrator_target is not None and latency > integrator_target:
                exceeded_integrator += 1
                if len(outliers) < _MAX_EXAMPLES:
                    outliers.append(
                        {
                            "turn_index": turn.get("turn_index", 0),
                            "session_id": turn.get("session_id", ""),
                            "total_ms": latency,
                            "phase_timings": _engine_summary(turn).get("phase_timings") or {},
                            "exceeded_threshold": "integrator_p95",
                        }
                    )
            if hosted_target is not None and latency > hosted_target:
                exceeded_hosted += 1

        timings = _engine_summary(turn).get("phase_timings") or {}
        if isinstance(timings, dict):
            for phase, value in timings.items():
                if isinstance(value, (int, float)):
                    phase_values.setdefault(str(phase), []).append(float(value))

    phase_timings = {
        phase: {
            "p50": _percentile(values, 50),
            "p95": _percentile(values, 95),
            "p99": _percentile(values, 99),
        }
        for phase, values in phase_values.items()
    }

    return {
        "section": "latency_impact_report",
        "targets": {
            "integrator_p95_target_ms": integrator_target,
            "hosted_p95_target_ms": hosted_target,
        },
        "aggregate": {
            "turn_count": len(totals),
            "p50_total_ms": _percentile(totals, 50),
            "p95_total_ms": _percentile(totals, 95),
            "p99_total_ms": _percentile(totals, 99),
            "exceeded_integrator_target_count": exceeded_integrator,
            "exceeded_hosted_target_count": exceeded_hosted,
        },
        "phase_timings": phase_timings,
        "outliers": outliers,
    }


def _section_recommended_path(
    turns: list[dict[str, Any]],
    prospect_inputs: dict[str, Any],
    latency_section: dict[str, Any],
) -> dict[str, Any]:
    total = len(turns)
    tier_counts = {tier: 0 for tier in _TIERS}
    turns_with_pii = 0
    escalation_turns = 0
    for turn in turns:
        tier_counts[_governance_tier(turn)] += 1
        summary = _engine_summary(turn)
        if summary.get("pii_detected"):
            turns_with_pii += 1
        if summary.get("escalation_detected"):
            escalation_turns += 1

    def _pct(count: int) -> float:
        return (count / total * 100.0) if total else 0.0

    latency_acceptable = (
        latency_section["aggregate"]["exceeded_integrator_target_count"] == 0
        and latency_section["aggregate"]["exceeded_hosted_target_count"] == 0
    )

    return {
        "section": "recommended_path",
        "recommended_deployment_profile": prospect_inputs.get("deployment_profile"),
        "recommended_jurisdiction_config": {
            "active_jurisdictions": list(prospect_inputs.get("active_jurisdictions") or []),
            "require_user_jurisdiction": True,
        },
        "expected_production_tier_distribution": {
            "tier_clean_pct": _pct(tier_counts["tier_clean"]),
            "tier_warning_pct": _pct(tier_counts["tier_warning"]),
            "tier_escalation_pct": _pct(tier_counts["tier_escalation"]),
        },
        "enforce_rollout": {
            "strategy": "all_flows",
            "subset_description": "Integrator-defined cohort description",
            "estimated_days_to_full_enforce": None,
        },
        "findings_summary": {
            "pii_risk": "low" if turns_with_pii == 0 else "moderate",
            "escalation_signal_rate": "low" if escalation_turns == 0 else "moderate",
            "compliance_gaps": [],
            "latency_acceptable": latency_acceptable,
        },
        "next_steps": ["Integrator-defined next step"],
    }


def _resolve_period(
    turns: list[dict[str, Any]],
    period_start_utc: str | None,
    period_end_utc: str | None,
) -> dict[str, Any]:
    timestamps = [t.get("timestamp_utc") for t in turns if t.get("timestamp_utc")]
    start = period_start_utc or (min(timestamps) if timestamps else None)
    end = period_end_utc or (max(timestamps) if timestamps else None)
    return {"start_utc": start, "end_utc": end}


def aggregate_shadow_report(
    turns: list[dict[str, Any]],
    *,
    period_start_utc: str | None = None,
    period_end_utc: str | None = None,
    prospect_inputs: dict[str, Any] | None = None,
    latency_targets: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Produce shadow_report_v1 JSON from persisted turn payloads."""
    prospect_inputs = prospect_inputs or {}
    latency_targets = latency_targets or {}
    period = _resolve_period(turns, period_start_utc, period_end_utc)

    latency_section = _section_latency(turns, latency_targets)

    sections = {
        "pii_phi_detection_summary": _section_pii(turns, period),
        "compliance_exposure_examples": _section_compliance(turns, prospect_inputs),
        "token_savings_calculation": _section_token_savings(turns, prospect_inputs),
        "envelope_evidence_sample": _section_envelope_sample(turns),
        "escalation_signal_count": _section_escalation(turns),
        "unsafe_flow_documentation": _section_unsafe_flows(turns),
        "latency_impact_report": latency_section,
        "recommended_path": _section_recommended_path(turns, prospect_inputs, latency_section),
    }

    return {
        "schema_version": "shadow_report_v1",
        "generated_at_utc": _now_utc_iso(),
        "period": period,
        "sections": sections,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: saski-shadow aggregate --input PATH --output PATH [--schema v1]."""
    parser = argparse.ArgumentParser(prog="saski-shadow")
    subparsers = parser.add_subparsers(dest="command")
    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Aggregate a shadow pilot report from a JSONL turn store."
    )
    aggregate_parser.add_argument("--input", required=True, help="Path to JSONL turn store.")
    aggregate_parser.add_argument("--output", required=True, help="Path to write report JSON.")
    aggregate_parser.add_argument("--schema", default="v1", help="Report schema version.")

    args = parser.parse_args(argv)
    if args.command != "aggregate":
        parser.print_help()
        return 2

    turns = load_turns_jsonl(args.input)
    report = aggregate_shadow_report(turns)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
