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
from ..analyzer.executor import _normalize_domains
from ..laws import (
    LAW_SET_SYNC_DATE,
    LAW_SET_VERSION,
    STARTER_LAWS,
    coverage_summary,
    match_laws,
)

# Required messaging strings.
COMPLIANCE_DISCLAIMER = (
    "This report reflects a starter set of laws and will expand as coverage "
    "grows. It does not apply private SASKI enforcement mappings, thresholds, "
    "or internal policy logic. Law matches are keyed on integrator-supplied "
    "jurisdiction and domain metadata. Shadow mode does not perform "
    "content-based jurisdiction inference or statute verification."
)
UPGRADE_MESSAGE = (
    "For comprehensive results, add the licensed SASKI engine to your VPC deployment. "
    "Contact SASKI Institute at info@techviz.us or www.techviz.us."
)
ESCALATION_DISCLAIMER = (
    "Escalation counts reflect baseline distress phrase-list matches only and are "
    "not clinical crisis detection."
)
TOKEN_SAVINGS_DISCLAIMER = (
    "Estimate only. Computed by transparent arithmetic from two "
    "integrator-supplied inputs (legacy_system_prompt_tokens and "
    "lean_product_prompt_tokens) applied to the governance-tier counts observed "
    "in shadow mode. It embeds no proprietary SASKI prompt-assembly logic beyond "
    "two documented, observable defaults: a regulated-mode safety-envelope floor "
    "(applied on governed turns for child, patient, and therapist modes) and a "
    "fixed warning append. Tier 3 (escalation) turns are counted as the full "
    "legacy cost avoided, because in enforce mode the LLM call would not be made. "
    "No LLM egress was suppressed during this session - shadow observed, it did "
    "not act. Dollar savings are never computed here; apply your own input cost "
    "per token: dollar_savings = tokens_saved x (your cost per token). Every "
    "computed output is null unless both required inputs are supplied."
)

# Honest scope statements surfaced inside detection-bearing sections so a
# reader cannot mistake baseline observation for full enforcement coverage.
DETECTION_LIMITATIONS = [
    "CSAM content detection requires an upstream classifier; this package does not detect CSAM.",
    "Output PII review uses the same regex patterns as input detection. Paraphrased or "
    "encoded PII in model responses (for example, word-spelled digits, substituted "
    "characters, or reworded identifiers) may not be detected.",
    "Distress detection uses a small baseline list of common crisis phrases plus "
    "integrator-supplied indicators. This is common phrase awareness only — not "
    "clinical crisis detection. The licensed SASKI SDK provides clinical-grade "
    "crisis detection without requiring phrase lists.",
    "Law matching uses integrator-supplied jurisdiction and domain metadata; "
    "no content-based jurisdiction inference.",
    "future_effective laws are surfaced for awareness and are not currently enforceable.",
]

# Attached alongside a zero detection count so an empty result is never read as
# a clean bill of health.
BASELINE_ONLY_CAVEAT = (
    "Baseline detection only. Absence of a finding is not evidence of compliance."
)

# Section 3 basis labels: makes it explicit whether numbers were calculated.
_TOKEN_BASIS_ESTIMATED = "estimated_from_integrator_inputs"
_TOKEN_BASIS_INSUFFICIENT = "insufficient_inputs"

# Token-savings model defaults. These are documented, observable defaults (not
# proprietary SASKI internals): governed turns in a regulated mode carry a small
# safety-envelope floor on top of the lean product prompt, and a warning turn
# appends a fixed number of tokens. Integrators may override both via
# prospect_inputs; absent an override the defaults below apply.
_REGULATED_MODES = ("child", "patient", "therapist")
_REGULATED_MODE_FLOOR_DEFAULT = 85.0
_WARNING_APPEND_DEFAULT = 50.0
_DOLLAR_SAVINGS_NOTE = (
    "Dollar savings = tokens_saved x (your input cost per token). "
    "This report intentionally does not compute a dollar figure."
)

_MAX_EXAMPLES = 10
_PII_BUCKETS = (
    "ssn",
    "phone",
    "email",
    "ip",
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
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            turns.append(json.loads(line))
    return turns


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    """Report-generation date (UTC) used to classify law effective dates."""
    return datetime.now(timezone.utc).date().isoformat()


def _split_laws_by_effective_date(
    laws: list[dict[str, Any]],
    today_iso: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition matched laws into (in_force, future_effective) buckets.

    A law is ``in_force`` when its ``effective_date`` is absent/blank or is a
    date on or before ``today_iso`` (ISO ``YYYY-MM-DD`` strings compare
    correctly lexicographically). It is ``future_effective`` only when its
    ``effective_date`` is a parseable date strictly after today. Laws are never
    dropped; an unparseable date is treated conservatively as in_force.
    """
    in_force: list[dict[str, Any]] = []
    future: list[dict[str, Any]] = []
    for law in laws:
        effective = str(law.get("effective_date") or "").strip()
        if len(effective) == 10 and effective > today_iso:
            future.append(law)
        else:
            in_force.append(law)
    return in_force, future


def _num(value: Any) -> float | None:
    """Coerce an integrator-supplied numeric input to float, else None.

    Booleans are rejected (``True``/``False`` are not valid token or price
    figures even though they are ``int`` subclasses).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


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
    by_type = dict.fromkeys((*_PII_BUCKETS, "other"), 0)
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
    section = {
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
    if turns_with_pii == 0:
        section["baseline_only_caveat"] = BASELINE_ONLY_CAVEAT
    return section


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


def _turn_domain(
    turn: dict[str, Any], prospect_inputs: dict[str, Any]
) -> str | list[str] | None:
    """Resolve the domain(s) for a turn, passed straight to ``match_laws``.

    Precedence: an explicit ``domains`` list on the turn, then a per-turn
    ``domain`` (string or list), then the engine_summary passthrough, then a
    single report-level fallback. When still empty, derives defaults from
    ``engine_summary.mode`` (same mapping as ``analyze_turn``). A single string
    stays a string for full backward compatibility; a list is passed through so
    one turn can surface laws across multiple domains.
    """
    summary = _engine_summary(turn)
    ctx: dict[str, Any] = {}

    plural = turn.get("domains")
    if isinstance(plural, list):
        cleaned = [str(d) for d in plural if isinstance(d, str) and d]
        if cleaned:
            ctx["domains"] = cleaned

    if not ctx:
        value = turn.get("domain") or summary.get("domain")
        if not value:
            value = prospect_inputs.get("domain")
        if isinstance(value, list):
            cleaned = [str(d) for d in value if isinstance(d, str) and d]
            if cleaned:
                ctx["domains"] = cleaned
        elif value:
            ctx["domain"] = str(value)

    domains, _ = _normalize_domains(ctx, summary.get("mode"))
    if not domains:
        return None
    if len(domains) == 1:
        return domains[0]
    return domains


def _section_compliance(
    turns: list[dict[str, Any]], prospect_inputs: dict[str, Any]
) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    reason_codes: set[str] = set()
    turns_with_compliance = 0
    turns_with_jurisdiction = 0
    user_jurisdiction_injected = False

    turns_with_jurisdiction_metadata = 0
    turns_with_law_match = 0
    matched_laws_by_id: dict[str, dict[str, Any]] = {}

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
                        "baseline_pii_signal": bool(summary.get("pii_detected")),
                        "pii_detection_method": "baseline_regex_only",
                        "pii_types": list(summary.get("pii_types") or []),
                        "escalation_detected": bool(summary.get("escalation_detected")),
                        "outcome": (
                            summary.get("outcome")
                            if summary.get("outcome") in _OUTCOME_KEYS
                            else None
                        ),
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

    # Label-and-surface (never filter) future-effective laws so a compliance
    # reader sees what is coming as well as what is already in force.
    in_force_laws, future_effective_laws = _split_laws_by_effective_date(
        matched_laws, _today_utc()
    )

    active = prospect_inputs.get("active_jurisdictions") or []
    section = {
        "section": "compliance_exposure_examples",
        "disclaimer": COMPLIANCE_DISCLAIMER,
        "upgrade_path": UPGRADE_MESSAGE,
        "detection_limitations": list(DETECTION_LIMITATIONS),
        "jurisdiction_config": {
            "active_jurisdictions": list(active),
            "user_jurisdiction_injected": user_jurisdiction_injected,
        },
        "examples": examples,
        "matched_laws": matched_laws,
        # Additive lifecycle view; matched_laws above stays the flat list for
        # backward compatibility.
        "matched_laws_by_status": {
            "in_force": in_force_laws,
            "future_effective": future_effective_laws,
        },
        "law_match_summary": {
            "turns_with_jurisdiction_metadata": turns_with_jurisdiction_metadata,
            "turns_with_law_match": turns_with_law_match,
            "unique_law_ids": [law["law_id"] for law in matched_laws],
            "future_effective_count": len(future_effective_laws),
            "no_match_statement": no_match_statement,
        },
        "aggregate": {
            "turns_with_compliance_decisions": turns_with_compliance,
            "turns_with_jurisdiction_decision": turns_with_jurisdiction,
            "unique_reason_codes": sorted(reason_codes),
        },
    }
    if turns_with_law_match == 0:
        section["baseline_only_caveat"] = BASELINE_ONLY_CAVEAT
    return section


def _section_token_savings(
    turns: list[dict[str, Any]],
    prospect_inputs: dict[str, Any],
) -> dict[str, Any]:
    """Transparent, two-input token-savings estimate.

    The integrator supplies just two figures; everything else is observed from
    the shadow run or comes from two documented, observable defaults. No
    proprietary SASKI constants and no dollar arithmetic. Every computed output
    stays ``None`` unless both required inputs are supplied.

    Integrator inputs (prospect_inputs):
      - ``legacy_system_prompt_tokens`` (L): the integrator's current ungoverned
        system-prompt cost per LLM turn.
      - ``lean_product_prompt_tokens`` (P): the governed lean product-prompt cost
        per LLM turn.
      Optional advanced overrides:
      - ``regulated_mode_floor_tokens`` (default 85): safety-envelope floor added
        to P on governed turns whose mode is child/patient/therapist.
      - ``warning_append_tokens`` (default 50): tokens appended on a Tier 2 turn.

    Per-turn arithmetic (mode-aware):
      floor      = regulated_mode_floor_tokens if turn mode is regulated else 0
      Tier 1     saved = max(0, L - (P + floor))
      Tier 2     saved = max(0, L - (P + floor + warning_append))
      Tier 3     saved = L            # enforce mode would not call the LLM at all
      tokens_saved = sum of per-turn saved across observed turns
    """
    tier_counts = dict.fromkeys(_TIERS, 0)
    blocked = 0
    regulated_turns = 0

    legacy = _num(prospect_inputs.get("legacy_system_prompt_tokens"))
    lean = _num(prospect_inputs.get("lean_product_prompt_tokens"))

    floor_override = _num(prospect_inputs.get("regulated_mode_floor_tokens"))
    warn_override = _num(prospect_inputs.get("warning_append_tokens"))
    regulated_floor = (
        floor_override if floor_override is not None else _REGULATED_MODE_FLOOR_DEFAULT
    )
    warning_append = (
        warn_override if warn_override is not None else _WARNING_APPEND_DEFAULT
    )

    total = len(turns)
    can_estimate = legacy is not None and lean is not None and total > 0

    tokens_saved: float | None = 0.0 if can_estimate else None
    tier_saved = {"tier_clean": 0.0, "tier_warning": 0.0, "tier_escalation": 0.0}

    for turn in turns:
        tier = _governance_tier(turn)
        tier_counts[tier] += 1
        summary = _engine_summary(turn)
        is_regulated = summary.get("mode") in _REGULATED_MODES
        if is_regulated:
            regulated_turns += 1
        if summary.get("would_block") or summary.get("outcome") == PublicOutcome.BLOCK.value:
            blocked += 1

        if can_estimate:
            floor = regulated_floor if is_regulated else 0.0
            tier1_governed = lean + floor
            if tier == "tier_warning":
                saved = max(0.0, legacy - (tier1_governed + warning_append))
            elif tier == "tier_escalation":
                saved = legacy  # full legacy cost avoided: LLM not called in enforce mode
            else:  # tier_clean
                saved = max(0.0, legacy - tier1_governed)
            tier_saved[tier] += saved
            tokens_saved += saved

    basis = _TOKEN_BASIS_ESTIMATED if can_estimate else _TOKEN_BASIS_INSUFFICIENT

    return {
        "section": "token_savings_calculation",
        "basis": basis,
        "disclaimer": TOKEN_SAVINGS_DISCLAIMER,
        "dollar_savings_note": _DOLLAR_SAVINGS_NOTE,
        "upgrade_path": UPGRADE_MESSAGE,
        "prospect_inputs": {
            "legacy_system_prompt_tokens": legacy,
            "lean_product_prompt_tokens": lean,
        },
        "measured_from_shadow": {
            "total_turns": total,
            "tier_clean_turns": tier_counts["tier_clean"],
            "tier_warning_turns": tier_counts["tier_warning"],
            "tier_escalation_turns": tier_counts["tier_escalation"],
            "regulated_mode_turns": regulated_turns,
            "would_have_blocked_turns": blocked,
            "shadow_mode_note": "enforcement not applied; counts reflect would_block signals only",
        },
        "token_model": {
            "regulated_modes": list(_REGULATED_MODES),
            "regulated_mode_floor_tokens": regulated_floor,
            "warning_append_tokens": warning_append,
            "tier3_llm_tokens": 0,
        },
        "savings": {
            "tokens_saved_estimate": tokens_saved,
            "tier_clean_tokens_saved": tier_saved["tier_clean"] if can_estimate else None,
            "tier_warning_tokens_saved": tier_saved["tier_warning"] if can_estimate else None,
            "tier_escalation_tokens_saved": (
                tier_saved["tier_escalation"] if can_estimate else None
            ),
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
    by_tier = dict.fromkeys(_TIERS, 0)
    by_outcome = dict.fromkeys(_OUTCOME_KEYS, 0)
    by_risk = dict.fromkeys(_RISK_BANDS, 0)
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
                        "llm_egress_would_be_suppressed": bool(summary.get("would_block")),
                        "shadow_actual_llm_response_hash": turn.get("output_hash")
                        or turn.get("response_hash"),
                    }
                )

    total = len(turns)
    section = {
        "section": "escalation_signal_count",
        "disclaimer": ESCALATION_DISCLAIMER,
        "upgrade_path": UPGRADE_MESSAGE,
        "detection_limitations": list(DETECTION_LIMITATIONS),
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
    if escalation_turns == 0:
        section["baseline_only_caveat"] = BASELINE_ONLY_CAVEAT
    return section


def _section_unsafe_flows(turns: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = {
        "enforcement_would_block": [],
        "policy_boundary_failure": [],
        "content_sanitization_gap": [],
        "integrator_override": [],
        "manual_review_required": [],
        "adversarial_probe": [],
        "clinical_intent_boundary": [],
        "other": [],
    }
    examples: list[dict[str, Any]] = []

    def _record(
        turn: dict[str, Any],
        category: str,
        recommended: str,
        extra_signals: dict[str, Any] | None = None,
    ) -> None:
        summary = _engine_summary(turn)
        deployment = turn.get("deployment_decision") or {}
        outcome = summary.get("outcome")
        signals: dict[str, Any] = {
            "enforcement_suppressed": bool(deployment.get("enforcement_suppressed")),
            "would_block": bool(summary.get("would_block")),
            "outcome": outcome if outcome in _OUTCOME_KEYS else None,
            "human_review_required": outcome == PublicOutcome.HUMAN_REVIEW.value,
        }
        if extra_signals:
            signals.update(extra_signals)
        finding = {
            "turn_index": turn.get("turn_index", 0),
            "session_id": turn.get("session_id", ""),
            "category": category,
            "signals": signals,
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

        if summary.get("adversarial_signal"):
            extra: dict[str, Any] = {}
            matches = summary.get("adversarial_matches")
            if isinstance(matches, list) and matches:
                extra["adversarial_matches"] = matches
            _record(
                turn,
                "adversarial_probe",
                "Review adversarial probe handling; route to licensed SDK adversarial detection",
                extra or None,
            )
        if summary.get("clinical_intent_signal"):
            extra = {}
            matches = summary.get("clinical_intent_matches")
            if isinstance(matches, list) and matches:
                extra["clinical_intent_matches"] = matches
            _record(
                turn,
                "clinical_intent_boundary",
                "Verify clinical boundary routing; do not present as licensed clinical care",
                extra or None,
            )

    return {
        "section": "unsafe_flow_documentation",
        "detection_limitations": list(DETECTION_LIMITATIONS),
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
    compliance_section: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = len(turns)
    tier_counts = dict.fromkeys(_TIERS, 0)
    turns_with_pii = 0
    escalation_turns = 0
    adversarial_fired = False
    clinical_intent_fired = False
    for turn in turns:
        tier_counts[_governance_tier(turn)] += 1
        summary = _engine_summary(turn)
        if summary.get("pii_detected"):
            turns_with_pii += 1
        if summary.get("escalation_detected"):
            escalation_turns += 1
        if summary.get("adversarial_signal"):
            adversarial_fired = True
        if summary.get("clinical_intent_signal"):
            clinical_intent_fired = True

    def _pct(count: int) -> float:
        return (count / total * 100.0) if total else 0.0

    latency_acceptable = (
        latency_section["aggregate"]["exceeded_integrator_target_count"] == 0
        and latency_section["aggregate"]["exceeded_hosted_target_count"] == 0
    )

    future_effective_count = 0
    if compliance_section:
        future_effective_count = (
            compliance_section.get("law_match_summary", {}).get("future_effective_count") or 0
        )

    next_steps: list[str] = []
    if adversarial_fired:
        next_steps.append(
            "Adversarial probes detected — configure licensed SDK adversarial "
            "detection before production deployment."
        )
    if clinical_intent_fired:
        next_steps.append(
            "Clinical boundary requests detected — verify licensed SDK clinical "
            "intent classification is configured for this deployment."
        )
    if escalation_turns > 0:
        next_steps.append(
            "Distress signals detected — verify crisis detection path with "
            "licensed SDK before production deployment."
        )
    if turns_with_pii > 0:
        next_steps.append(
            "PII detected in user messages — verify licensed SDK HIPAA-tier "
            "redaction is configured for jurisdiction and mode."
        )
    if future_effective_count > 0:
        next_steps.append(
            "Future-effective laws matched — schedule registry update reviews "
            "before effective dates."
        )
    next_steps.append(
        "Contact info@techviz.us to configure the licensed SASKI SDK for production enforcement."
    )

    if escalation_turns > 0:
        subset_description = "Prioritize crisis and distress flows"
    elif turns_with_pii > 0:
        subset_description = "Prioritize PII-handling flows"
    else:
        subset_description = "All observed session flows"

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
            "subset_description": subset_description,
            "estimated_days_to_full_enforce": None,
        },
        "findings_summary": {
            "pii_risk": "low" if turns_with_pii == 0 else "moderate",
            "escalation_signal_rate": "low" if escalation_turns == 0 else "moderate",
            "compliance_gaps": [],
            "latency_acceptable": latency_acceptable,
        },
        "next_steps": next_steps,
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


def _section_sdk_integration_signals(
    turns: list[dict[str, Any]],
    sections: dict[str, Any],
) -> dict[str, Any]:
    """Derive actionable integration signals from the already-built report sections.

    Each signal fires only when its condition is met — no signal is emitted when
    the condition is false. Signal text describes observable shadow behavior and
    SDK configuration guidance only. No numeric thresholds, no SDK module names,
    no enforcement decision logic.
    """
    signals: list[dict[str, Any]] = []

    pii_section = sections["pii_phi_detection_summary"]
    compliance_section = sections["compliance_exposure_examples"]
    escalation_section = sections["escalation_signal_count"]

    turns_with_pii: int = pii_section["totals"]["turns_with_pii"]
    escalation_turns: int = escalation_section["totals"]["escalation_turns"]
    total_turns: int = escalation_section["totals"]["turns_processed"]
    future_effective: list = compliance_section["matched_laws_by_status"]["future_effective"]

    # Distinct domains and multi-domain turn count derived from the turn store.
    all_domains: set[str] = set()
    multi_domain_turns = 0
    for turn in turns:
        td = turn.get("domains")
        if isinstance(td, list) and len(td) > 1:
            multi_domain_turns += 1
            for d in td:
                if isinstance(d, str) and d:
                    all_domains.add(d)
        else:
            val = turn.get("domain") or _engine_summary(turn).get("domain")
            if isinstance(val, list):
                for d in val:
                    if isinstance(d, str) and d:
                        all_domains.add(d)
            elif isinstance(val, str) and val:
                all_domains.add(val)

    by_outcome = escalation_section.get("by_outcome", {})
    crisis_turns = by_outcome.get("crisis_referral", 0) + by_outcome.get(
        "physical_emergency_referral", 0
    )

    # SIS-001 — Distress without licensed detection
    if escalation_turns > 0 and "detection_limitations" in escalation_section:
        signals.append(
            {
                "signal_id": "SIS-001",
                "category": "distress_detection",
                "severity": "action_required",
                "title": "Real distress detection requires licensed engine",
                "observation": (
                    f"Shadow detected {escalation_turns} escalation signal"
                    f"{'s' if escalation_turns != 1 else ''}. Baseline detection uses a "
                    "small list of common crisis phrases plus integrator-supplied "
                    "indicators. The licensed SASKI SDK provides clinical-grade crisis "
                    "detection without phrase lists and catches indirect, contextual, and "
                    "semantic crisis signals the baseline cannot."
                ),
                "sdk_recommendation": (
                    "Configure the licensed SASKI SDK with mode-appropriate crisis "
                    "thresholds. The SDK's built-in distress detection operates without "
                    "requiring integrator-supplied indicator lists."
                ),
                "affected_turns": escalation_turns,
                "contact": "info@techviz.us",
            }
        )

    # SIS-002 — Future-effective laws in active jurisdictions
    if future_effective:
        n_future = len(future_effective)
        signals.append(
            {
                "signal_id": "SIS-002",
                "category": "compliance_readiness",
                "severity": "warning",
                "title": "Upcoming compliance obligations detected",
                "observation": (
                    f"{n_future} future-effective law"
                    f"{'s' if n_future != 1 else ''} matched for this session's "
                    "jurisdictions. These are not yet enforceable but will become active "
                    "on their effective dates."
                ),
                "sdk_recommendation": (
                    "Review the future_effective law list and verify your SDK jurisdiction "
                    "configuration will be updated before each law's effective date. "
                    "Contact info@techviz.us for registry update notifications."
                ),
                "affected_turns": compliance_section["law_match_summary"][
                    "turns_with_law_match"
                ],
                "contact": "info@techviz.us",
            }
        )

    # SIS-003 — Multi-domain turns with single-domain session context
    if multi_domain_turns > 0:
        signals.append(
            {
                "signal_id": "SIS-003",
                "category": "domain_configuration",
                "severity": "info",
                "title": "Multi-domain coverage active",
                "observation": (
                    f"{multi_domain_turns} turn"
                    f"{'s' if multi_domain_turns != 1 else ''} used multi-domain matching. "
                    "This requires explicit domain list configuration per turn."
                ),
                "sdk_recommendation": (
                    "Verify your integration passes the correct domain context per turn. "
                    "The licensed SDK enforces domain-specific obligations independently — "
                    "misconfigured domain metadata may result in missed obligations."
                ),
                "affected_turns": multi_domain_turns,
                "contact": "info@techviz.us",
            }
        )

    # SIS-004 — PII detected without licensed redaction
    if turns_with_pii > 0:
        pii_types = pii_section["history_redaction"]["aggregate_pii_types_found"]
        pii_types_str = ", ".join(pii_types) if pii_types else "unknown"
        signals.append(
            {
                "signal_id": "SIS-004",
                "category": "pii_redaction",
                "severity": "action_required",
                "title": "PII detected — licensed redaction recommended",
                "observation": (
                    f"Shadow detected PII in {turns_with_pii} turn"
                    f"{'s' if turns_with_pii != 1 else ''} ({pii_types_str} types). "
                    "Baseline detection uses regex patterns only. The licensed SDK "
                    "provides HIPAA Safe Harbor redaction with jurisdiction-aware overrides."
                ),
                "sdk_recommendation": (
                    "Enable the licensed SASKI SDK for production PII handling. Configure "
                    "mode and jurisdiction to activate the appropriate redaction tier for "
                    "your deployment."
                ),
                "affected_turns": turns_with_pii,
                "contact": "info@techviz.us",
            }
        )

    # SIS-005 — Cross-domain isolation not verified
    if len(all_domains) > 1:
        signals.append(
            {
                "signal_id": "SIS-005",
                "category": "cross_domain_isolation",
                "severity": "info",
                "title": "Cross-domain isolation not explicitly tested",
                "observation": (
                    f"This session included {len(all_domains)} domains. Cross-domain law "
                    "isolation (ensuring healthcare laws do not surface in employment turns, "
                    "etc.) was not explicitly verified in this run."
                ),
                "sdk_recommendation": (
                    "Run the shadow compliance harness with cross-domain negative tests "
                    "before production deployment. Contact info@techviz.us for integration "
                    "validation support."
                ),
                "affected_turns": total_turns,
                "contact": "info@techviz.us",
            }
        )

    # SIS-006 — No crisis floor verified
    if crisis_turns == 0 and total_turns > 5:
        signals.append(
            {
                "signal_id": "SIS-006",
                "category": "crisis_detection_coverage",
                "severity": "warning",
                "title": "Crisis detection floor not exercised in this session",
                "observation": (
                    "No crisis-level signals were detected in this session. Shadow mode "
                    "cannot verify crisis detection coverage — is_crisis is always False "
                    "in the baseline package."
                ),
                "sdk_recommendation": (
                    "The licensed SASKI SDK provides a multi-level crisis detection floor "
                    "including immutable 988 templates and physical emergency referrals. "
                    "Verify crisis paths separately using the licensed engine before "
                    "production deployment."
                ),
                "affected_turns": 0,
                "contact": "info@techviz.us",
            }
        )

    n = len(signals)
    category_count = len({s["category"] for s in signals})
    if n > 0:
        summary = (
            f"{n} integration signal{'s' if n != 1 else ''} detected across "
            f"{category_count} categor{'ies' if category_count != 1 else 'y'}"
        )
    else:
        summary = "No integration signals detected for this session"

    return {
        "section": "sdk_integration_signals",
        "summary": summary,
        "signals": signals,
    }


def _coverage_notice(
    turns: list[dict[str, Any]],
    sections: dict[str, Any],
) -> dict[str, Any]:
    """Name the observable capabilities that were NOT exercised in this run.

    An empty or all-zero section can read as "nothing found" when the honest
    meaning is "not measured this run because its inputs were absent". This
    banner states, factually and for this run only, which capabilities produced
    no signal because they were never fed the inputs they need. It makes no
    safety claim and asserts nothing about content; it only distinguishes
    "not evaluated" from "evaluated and clear".
    """
    # Output review only runs when an assistant reply is reviewed; when it does,
    # the turn carries the review's observable keys. Their absence everywhere
    # means no post-LLM output review happened (e.g. provider=none, or a runner
    # that never feeds replies back through review_output).
    review_keys = ("pii_leaked_types", "human_escalation_claimed", "policy_boundary_hits")
    review_performed = any(
        any(k in (turn.get("output_review") or {}) for k in review_keys) for turn in turns
    )
    policy_evaluated = any((turn.get("compliance_decisions") or []) for turn in turns)
    token_basis = sections["token_savings_calculation"]["basis"]
    pricing_supplied = token_basis == _TOKEN_BASIS_ESTIMATED

    inactive: list[str] = []
    if not review_performed:
        inactive.append(
            "Post-LLM output review was not performed this run. Unsafe Flow "
            "Documentation therefore reflects no review of model output - an empty "
            "result here means 'not evaluated', not 'no unsafe flows'. Feed each "
            "model reply back through output review to populate it."
        )
    if not policy_evaluated:
        inactive.append(
            "No integrator policy rules were evaluated. Compliance Exposure shows "
            "matched public laws by jurisdiction and domain only, not policy-rule "
            "decisions."
        )
    if not pricing_supplied:
        inactive.append(
            "Token-savings inputs were not supplied, so savings figures are null. "
            "Observed governance-tier counts are still reported."
        )

    return {
        "all_capabilities_active": not inactive,
        "inactive_capabilities": inactive,
        "details": {
            "post_llm_output_review": "performed" if review_performed else "not_performed",
            "integrator_policy_rules": "evaluated" if policy_evaluated else "not_evaluated",
            "token_savings_inputs": "supplied" if pricing_supplied else "not_supplied",
            "distress_detection": "integrator_indicator_dependent",
        },
    }


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
    compliance_section = _section_compliance(turns, prospect_inputs)

    sections = {
        "pii_phi_detection_summary": _section_pii(turns, period),
        "compliance_exposure_examples": compliance_section,
        "token_savings_calculation": _section_token_savings(turns, prospect_inputs),
        "envelope_evidence_sample": _section_envelope_sample(turns),
        "escalation_signal_count": _section_escalation(turns),
        "unsafe_flow_documentation": _section_unsafe_flows(turns),
        "latency_impact_report": latency_section,
        "recommended_path": _section_recommended_path(
            turns, prospect_inputs, latency_section, compliance_section
        ),
    }
    sections["sdk_integration_signals"] = _section_sdk_integration_signals(turns, sections)

    coverage = coverage_summary()
    methodology = {
        "detector_profile": "baseline-v1",
        "law_set_version": LAW_SET_VERSION,
        "law_set_sync_date": LAW_SET_SYNC_DATE,
        "total_laws_evaluated": len(STARTER_LAWS),
        "total_jurisdictions": coverage["total_states"],
        "schema_version": "shadow_report_v1",
        "report_period": {
            "start_utc": period.get("start_utc"),
            "end_utc": period.get("end_utc"),
        },
    }

    return {
        "schema_version": "shadow_report_v1",
        "generated_at_utc": _now_utc_iso(),
        "period": period,
        "methodology": methodology,
        "coverage_notice": _coverage_notice(turns, sections),
        "sections": sections,
    }


def _load_config(path: str | None) -> dict[str, Any]:
    """Load an optional runtime config (pricing/token-model/period) JSON.

    Recognized keys: ``prospect_inputs`` (dict, includes the token model and
    pricing fields used by the token-savings section), ``latency_targets``
    (dict), ``period_start_utc`` and ``period_end_utc`` (strings). Unknown keys
    are ignored. Everything is integrator-supplied; there are no defaults.
    """
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object at the top level.")
    return data


def main(argv: list[str] | None = None) -> int:
    """CLI: saski-shadow aggregate --input PATH --output PATH [--config PATH]."""
    parser = argparse.ArgumentParser(prog="saski-shadow")
    subparsers = parser.add_subparsers(dest="command")
    aggregate_parser = subparsers.add_parser(
        "aggregate", help="Aggregate a shadow pilot report from a JSONL turn store."
    )
    aggregate_parser.add_argument("--input", required=True, help="Path to JSONL turn store.")
    aggregate_parser.add_argument("--output", required=True, help="Path to write report JSON.")
    aggregate_parser.add_argument("--schema", default="v1", help="Report schema version.")
    aggregate_parser.add_argument(
        "--config",
        default=None,
        help=(
            "Optional JSON config with integrator inputs: prospect_inputs "
            "(token model + pricing for the token-savings estimate), "
            "latency_targets, period_start_utc, period_end_utc."
        ),
    )

    args = parser.parse_args(argv)
    if args.command != "aggregate":
        parser.print_help()
        return 2

    config = _load_config(args.config)
    turns = load_turns_jsonl(args.input)
    report = aggregate_shadow_report(
        turns,
        period_start_utc=config.get("period_start_utc"),
        period_end_utc=config.get("period_end_utc"),
        prospect_inputs=config.get("prospect_inputs"),
        latency_targets=config.get("latency_targets"),
    )
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
