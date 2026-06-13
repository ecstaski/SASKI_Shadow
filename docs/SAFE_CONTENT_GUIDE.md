# saski-shadow — Safe Content Migration Guide

**Version:** 0.1.0-draft  
**Purpose:** IP-safe extraction instructions for each source file in the private `sasi-sdk` repository  
**Rule:** When in doubt, leave it out. Flag uncertain items for human review.

---

## Source Files Read (Confirmed)

All nine required source files were read in full at the expected paths:

1. `sasi_sdk/deployment_mode.py` ✓
2. `sasi_sdk/evidence_export.py` ✓
3. `sasi_sdk/core/canonical.py` ✓
4. `sasi_sdk/core/cem_artifacts.py` ✓
5. `sasi_sdk/core/envelope.py` ✓
6. `sasi_sdk/result.py` ✓
7. `sasi_sdk/enums.py` ✓
8. `sasi_sdk/exceptions.py` ✓
9. `tests/test_evidence_export_research.py` ✓

---

## Detector IP Constraints

The new detector modules must never contain:

- SASKI crisis detection phrases, thresholds, or semantic anchors
- MDTSAS dimension names or weights
- Private PII patterns from `sasi_sdk/core/pii.py`
- Jurisdiction fallback values or statute logic
- Symbolic operator names or tag taxonomy
- Obfuscation detection thresholds or algorithm
- Any numeric threshold that matches private sasi-sdk configuration values
- Any import from sasi-sdk modules

The distress phrase list in `detectors/distress.py` must contain only phrases that would appear in publicly available mental health first aid resources or academic literature. Nothing proprietary.

The PII patterns in `detectors/pii.py` must use only standard publicly documented regex patterns for US identifiers. Nothing from private `sasi_sdk/core/pii.py`.

---

## Per-File Migration Table

| Source file (sasi-sdk) | Target file (saski-shadow) | Include verbatim | Strip entirely | Replace with safe alternative | Flag for human review |
|------------------------|------------------------------|------------------|----------------|-------------------------------|----------------------|
| `deployment_mode.py` | `deployment.py` | `DeploymentMode`, `DeploymentDecision`, `evaluate_deployment_mode()`, `_normalize_mode()`, `to_dict()` | Docstring references to "core decision engine", "risk scoring", "POC/pilot sales cycles", "Phase A" label | `AnalysisResult` protocol type hint instead of `SaskiResult`; generic reason strings without engine references | Comment "Phase A" in module docstring |
| `evidence_export.py` | `evidence.py` | `MODE_TAG_ENUM`, `OUTCOME_STATUS_ENUM`, `RAW_TEXT_KEYS`, `normalize_output_text_for_hashing`, `compute_output_hash`, `turn_payload_from_result`, `build_evidence_bundle`, `generate_batch_manifest`, `record_research_event`, `update_bundle_outcome`, all `_validate_*` helpers, `_ordered_turns`, `_canonical_turns_for_checksum`, `_to_epoch_ms`, `_resolve_output_hash`, `_extract_envelope_field` | `ACTION_LABEL_ENUM` values `FALSE_POSITIVE_USER_RETRY`, `INJECTION_ATTEMPT_DETECTED`; `_infer_action_label_from_result` logic referencing `disclosure_guard`, `immediate_988`, `obfuscation_detected`, `crisis_summary`; module docstring "hospital/insurer-grade"; `get_audit_record()` passthrough of full engine audit | `infer_export_action_label()` using only `should_block`, `pii_detected`, redacted vs egress length delta, and generic monitoring flag; optional slim `audit_record` with `outcome`, `risk_band`, `pii_detected` only; `ExportActionLabel` enum with four values only | Whether `get_audit_record()` passthrough is safe if engine supplies it; `DEFAULT_POLICY_HASH` placeholder constant; `compute_llm_payload_hash` field names `message_for_llm` etc. in internal canonical payload (not exported) |
| `core/canonical.py` | `hashing.py` | `canonical_dumps`, `canonical_bytes`, `sha256_hex`, `hash_message`, `_quantize_float`, `_to_canonical_value`, float quantization constant | `policy_hash_from_config()` and its docstring referencing config thresholds and safeguard lists | `CanonicalSerializationError` defined locally in `hashing.py` or `exceptions.py` | Docstring "8 decimal places" numeric precision constant; `policy_hash_from_config` omission may break partners expecting it — confirm public API need |
| `core/cem_artifacts.py` | `schemas/transport_audit_v1.json` + type hints in `types.py` only | Field names and types from `TransportAuditRecord.to_dict()` **except** CEM-related naming; `artifact_hash()` function body | Entire module docstring; `HardStateTransitionSignal` class; all comments referencing validation methodology; `now_utc_iso()` (reimplement inline or in evidence.py) | JSON Schema document only — no Python dataclass named after private artifact types; refer to `transport_audit_record` as opaque dict validated against schema; `jurisdiction_source` enum: `integrator_supplied`, `not_provided`, `unknown` only | `sasi_envelope_attestation` nested object shape; `violation_events` opaque array structure; 32-char vs 64-char hash truncation in `artifact_hash` |
| `core/envelope.py` | `schemas/envelope_v1.json` only | `ENVELOPE_VERSION` constant concept; hash/timestamp/id fields in reduced schema | `SASIEnvelope` dataclass; `_scrub_score_like_values`; `routing_decision` property and mapping; `controls_snapshot`, `reconstruction_artifacts`, `evidence_snapshot`, `confidence_metadata`, `decision_path`, `primary_triggers`, `provable_logs`, `active_safeguards_at_decision`; full `to_dict()` | Public schema with `run_id`, `policy_id`, `policy_hash`, `timestamp_utc`, `input_hash`, `output_hash`, `integrator_signature`, `events[]`, `invariant_summary{}` only; envelope passthrough in turn payload without transformation | Whether `output_hash` belongs in envelope schema vs turn payload only |
| `result.py` | `types.py` (protocol only) | Nothing verbatim from `SaskiResult` or `MDTSASScores` | Entire `SaskiResult` dataclass; `MDTSASScores` and weight formulas; `get_audit_record()` full implementation; `to_dict()`; `_scrub_score_like_values`; `restore_placeholders()`; all tag/operator/pipeline fields | `AnalysisResult` Protocol with minimal fields listed in PACKAGE_SPEC; optional `MinimalAuditRecord` TypedDict with `timestamp`, `outcome`, `risk_band`, `pii_detected`, `pii_types` | Field list for Protocol — `metadata` dict passthrough may leak engine internals if integrator stores full engine metadata in turn JSONL |
| `enums.py` | `enums.py` (slim) | `DeploymentMode` values (as part of deployment.py enums), `ModeTag` derived from `MODE_TAG_ENUM` | `SafetyTier`, `PIILevel`, `Mode`, `HookType`, `CrisisType`, `CrisisSeverity`, `LLMProvider`, full `Action`, full `RiskLevel` with clinical docstrings | `PublicOutcome`, `ExportActionLabel`, `OutcomeStatus` only; map engine actions in adapter layer | Whether `RiskLevel` values (`safe`, `moderate`, `elevated`, `imminent`) are safe for report aggregation section 5 — they appear in shadow report schema |
| `exceptions.py` | `hashing.py` or `exceptions.py` | `CanonicalSerializationError` class body (empty pass) | All other exception classes and fail-closed crisis docstrings | `ShadowError` base exception optional | None beyond class naming |
| `tests/test_evidence_export_research.py` | `tests/test_*.py` | Test logic patterns (hash normalization, strict boundary, manifest checksums) | `DummyResult` using `Action.CONTINUE`, `Action.MONITOR`; strings `"hello"` as message content; `gpt-test`, `openai` provider names tied to real vendors | `StubResult` with generic `action="allow"`, `should_block=False`, hex-only hashes, `session_id="sess_test_001"` | `test_action_mapping_monitor_and_block_and_rewrite` — uses `pii_detected` and `should_block` which reveal inference rules; keep tests but use neutral field names |

---

## Additional Source References (Not in Required Read List)

These files are **not** migrated but inform behavior. Do **not** copy content from them into the public package:

| File | Why referenced | Action |
|------|----------------|--------|
| `docs/SHADOW_MODE_REPORT_SCHEMA.md` (sections 1–8) | Report section shapes for `shadow_report_v1.json` | Use IP-sanitized shapes only; skip internal appendix entirely |
| `sasi_sdk/core/sasi_envelope_attestation.py` | Nested under transport audit in engine | Do not migrate; treat `sasi_envelope_attestation` as opaque object in schema |
| `sasi_sdk/session.py` | Creates transport audit and envelope | Do not read or port; public package receives pre-built metadata dicts |

---

## Adapter Metadata Allowlist (`integrations/saski_sdk.py`)

The adapter may **only** pass these fields from engine metadata into the turn payload `engine_summary` block:

| Field | Constraint |
|-------|------------|
| `outcome` | Mapped to `PublicOutcome` value |
| `risk_band` | `low`, `moderate`, `elevated`, `critical` only |
| `pii_detected` | Boolean |
| `pii_types` | Array of generic category strings only |
| `escalation_detected` | Boolean |
| `would_block` | Boolean |
| `governance_tier` | Pre-computed string: `tier_clean`, `tier_warning`, `tier_escalation` |
| `phase_timings` | Opaque dict of string → float |

The adapter must **never** pass:

- MDTSAS scores or dimension names
- `safety_tags` or operator tags
- `obfuscation_score` or `obfuscation_detected`
- `crisis_summary` or `message_for_llm` text
- `routing_decision` or `recommended_pipeline`
- Any numeric threshold values
- Any internal module or method names

---

## Aggregator Governance Tier Rule

The aggregator reads the pre-computed `governance_tier` field from the `engine_summary` block in each turn payload. It does **not** re-derive or re-implement tier classification logic. If `governance_tier` is absent from a turn, the aggregator assigns `tier_clean` as the safe default.

---

## Safe Replacement Patterns (Summary)

| Private pattern | Public replacement |
|-----------------|-------------------|
| `SaskiResult` | `AnalysisResult` Protocol |
| `from sasi_sdk.core.canonical import ...` | `from saski_shadow.hashing import ...` |
| `TransportAuditRecord` dataclass | `transport_audit_v1.json` schema validation |
| `SASIEnvelope.to_dict()` full output | Filter to `envelope_v1.json` allowed fields only |
| `get_audit_record()` full dict | `MinimalAuditRecord` or omit from strict export |
| `_infer_action_label_from_result` | `infer_export_action_label` with four safe signals |
| Engine `action` strings | `PublicOutcome` via `map_public_outcome()` |
| `latency_breakdown` phase keys | `phase_timings: dict[str, float]` |
| Compliance `reason_code` examples | `COMPLIANCE_REASON_CODE` placeholder string |
| Token model constants | `prospect_inputs` user-supplied placeholders |
