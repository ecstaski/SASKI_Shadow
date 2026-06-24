"""Convert a ``BaselineAnalysisResult`` into the JSONL turn shape the shadow
report aggregator consumes.

This closes the silent-failure gap identified in research: nothing in the repo
previously turned an ``analyze_turn()`` result into the persisted turn record
that ``aggregate_shadow_report()`` reads, so a report could render empty
sections with no error if a hand-rolled adapter was wrong.

--------------------------------------------------------------------------------
What the aggregator (saski_shadow/aggregate/report.py) reads from each turn
--------------------------------------------------------------------------------
Top-level keys:
  - turn_index        : int                     (all sections, examples)
  - session_id        : str                      (all sections, examples)
  - timestamp_utc     : str | None               (report period resolution)
  - input_hash        : str | None               (PII / escalation examples)
  - output_hash       : str | None               (escalation / unsafe examples;
                        response_hash is also accepted as a fallback)
  - response_hash     : str | None               (fallback for output_hash)
  - latency_ms        : int | float              (latency section)
  - mode_tag          : str (ModeTag value)      (envelope sample)
  - envelope          : dict                      (envelope sample)
  - jurisdiction      : str | None               (section 2 law matching;
                        engine_summary.user_jurisdiction is also accepted)
  - domain / domains  : str | list[str] | None    (section 2 law matching;
                        engine_summary.domain is also accepted)
  - engine_summary    : dict                      (central; see below)
  - transport_audit_record : dict                 (PII + section 2)
  - compliance_decisions   : list[dict]           (section 2)
  - output_review     : dict                      (unsafe-flow section)
  - deployment_decision : dict                    (unsafe-flow / section 2;
                        falls back to engine_summary.would_block when absent)

engine_summary keys read: outcome, risk_band, pii_detected, pii_types,
  escalation_detected, would_block, governance_tier, phase_timings,
  user_jurisdiction, domain, mode.

transport_audit_record keys read: jurisdiction_source, redaction_applied,
  message_for_llm_hash, pii_types.

--------------------------------------------------------------------------------
Gap vs evidence.turn_payload_from_result()
--------------------------------------------------------------------------------
``turn_payload_from_result()`` is the hash-only evidence serializer. Its
``_build_engine_summary()`` deliberately emits a SLIM summary -- only
``outcome``, ``risk_band``, and ``pii_detected``. It drops ``governance_tier``,
``pii_types``, ``escalation_detected``, ``would_block``, ``phase_timings``,
``user_jurisdiction``, ``domain``, and ``mode``. The aggregator depends on all
of those, so a turn produced by ``turn_payload_from_result()`` yields a report
with empty tier/escalation/law/latency-phase data. This adapter instead carries
the analyzer's full ``engine_summary`` (and the transport, compliance, and
output-review blocks) straight through, which is exactly what the aggregator
needs. (Closing the same gap inside the evidence serializer is a separate task.)
"""

from __future__ import annotations

from typing import Any

from ..analyzer.executor import BaselineAnalysisResult

# Map the analyzer's enforcement_mode onto a public ModeTag value for the
# envelope-sample section. Defaults to "shadow_mode".
_ENFORCEMENT_TO_MODE_TAG = {
    "enforce": "saski_on",
    "warn": "warn_mode",
    "shadow": "shadow_mode",
}


def result_to_jsonl_turn(
    result: BaselineAnalysisResult,
    session_id: str,
    turn_index: int,
    provider_id: str | None = None,
) -> dict:
    """Build one aggregator-ready JSONL turn dict from a ``BaselineAnalysisResult``.

    Uses only values already present on ``result``. Fields the aggregator can
    read but the result does not provide are set to ``None`` (documented inline);
    the aggregator tolerates those via its own fallbacks.
    """
    metadata: dict[str, Any] = result.metadata or {}
    engine_summary: dict[str, Any] = dict(metadata.get("engine_summary") or {})
    transport: dict[str, Any] = dict(metadata.get("transport_audit_record") or {})
    envelope: dict[str, Any] = dict(result.envelope or {})

    enforcement_mode = str(transport.get("enforcement_mode", "shadow")).lower()
    mode_tag = _ENFORCEMENT_TO_MODE_TAG.get(enforcement_mode, "shadow_mode")

    return {
        "turn_index": int(turn_index),
        "session_id": session_id,
        # Hashes and timestamp live on the analyzer envelope; hoist to top level
        # where the aggregator looks for them.
        "timestamp_utc": envelope.get("timestamp_utc"),
        "input_hash": envelope.get("input_hash"),
        "output_hash": envelope.get("output_hash"),
        # response_hash is a separate post-LLM hash the baseline pipeline does
        # not compute; the aggregator falls back to output_hash when it is None.
        "response_hash": None,
        "latency_ms": float(result.pipeline_ms),
        "mode_tag": mode_tag,
        "model_id": result.model_id,
        # provider_id is supplied by the caller (FULL_PIPELINE wiring), not the
        # baseline result, which never calls a provider.
        "provider_id": provider_id if provider_id is not None else result.provider_id,
        # Convenience top-level mirrors of the jurisdiction/domain the aggregator
        # matches laws on. engine_summary carries the same values as a fallback.
        "jurisdiction": engine_summary.get("user_jurisdiction"),
        "domain": engine_summary.get("domain"),
        "envelope": envelope,
        # The analyzer's full engine_summary (tier, escalation, timings, mode,
        # jurisdiction, domain) -- the block the slim evidence serializer drops.
        "engine_summary": engine_summary,
        "transport_audit_record": transport,
        "compliance_decisions": list(metadata.get("compliance_decisions") or []),
        "output_review": dict(metadata.get("output_review") or {}),
        # deployment_decision comes from evaluate_deployment_mode(), a separate
        # call the analyzer result does not include. Left None; the aggregator
        # falls back to engine_summary.would_block for enforcement signals.
        "deployment_decision": None,
    }
