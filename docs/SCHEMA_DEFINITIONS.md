# saski-shadow — Schema Definitions

**Version:** 0.1.0-draft  
**Purpose:** Complete JSON structures for the three public schemas shipped in `saski_shadow/schemas/`  
**Constraint:** No engine internals, no methodology references, no threshold values, no statute names

---

## Schema Index

| File | Purpose |
|------|---------|
| `envelope_v1.json` | Hash-only analysis envelope attached to turn payloads |
| `transport_audit_v1.json` | Transport-boundary audit record (opaque structured field) |
| `shadow_report_v1.json` | Eight-section shadow pilot report produced by aggregator |

Schemas below are specified as JSON documents. The build session may convert them to JSON Schema Draft 2020-12 with equivalent constraints.

---

## 1. envelope_v1.json

### Intent

Public, hash-only envelope for regulator-readable evidence. Contains identity, timing, policy pinning, and opaque event summaries. No raw message text.

### Included fields

`run_id`, `policy_id`, `policy_hash`, `timestamp_utc`, `input_hash`, `output_hash`, `integrator_signature`, `events`, `invariant_summary`

### Excluded fields (must not appear)

`reconstruction_artifacts`, `controls_snapshot`, `routing_decision`, `evidence_snapshot`, `confidence_metadata`, `decision_path`, `primary_triggers`, `provable_logs`, `sdk_version`, `mode`, `risk_level`, `actions_taken`, `processing_ms`, `context_hash`, `llm_profile_id`

### Complete structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.saski.dev/envelope/v1",
  "title": "SASKI Shadow Envelope v1",
  "type": "object",
  "required": [
    "envelope_version",
    "run_id",
    "timestamp_utc",
    "input_hash"
  ],
  "additionalProperties": false,
  "properties": {
    "envelope_version": {
      "type": "string",
      "const": "1.0"
    },
    "run_id": {
      "type": "string",
      "minLength": 1,
      "description": "Unique turn/run identifier"
    },
    "policy_id": {
      "type": ["string", "null"],
      "description": "Pinned policy identifier supplied by engine"
    },
    "policy_hash": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{64}$",
      "description": "SHA-256 hex of pinned policy configuration"
    },
    "timestamp_utc": {
      "type": "string",
      "format": "date-time",
      "description": "ISO-8601 UTC timestamp of analysis"
    },
    "input_hash": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$",
      "description": "SHA-256 hex of analyzed input (no raw text)"
    },
    "output_hash": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{64}$",
      "description": "SHA-256 hex of normalized model output when available"
    },
    "integrator_signature": {
      "type": ["string", "null"],
      "description": "Optional integrator-defined field. saski-shadow does not generate or verify this value. Provided so integrators may attach their own signing, notarization, or chain-of-custody mechanism."
    },
    "events": {
      "type": "array",
      "description": "Opaque event summaries; no internal event registry exposed",
      "items": {
        "type": "object",
        "additionalProperties": true
      },
      "default": []
    },
    "invariant_summary": {
      "type": "object",
      "description": "Opaque invariant check summary",
      "additionalProperties": true,
      "default": {}
    }
  }
}
```

### Example instance (IP-safe)

```json
{
  "envelope_version": "1.0",
  "run_id": "run_a1b2c3d4",
  "policy_id": "policy_default",
  "policy_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "timestamp_utc": "2026-06-12T16:00:00+00:00",
  "input_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "output_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "integrator_signature": null,
  "events": [],
  "invariant_summary": {}
}
```

---

## 2. transport_audit_v1.json

### Intent

Opaque transport-boundary audit record proving governed egress metadata. Field names and types are public; creation logic stays in the licensed engine.

### Included fields

`record_version`, `run_id`, `enforcement_mode`, `jurisdiction_source`, `pii_detected`, `pii_types`, `redaction_applied`, `message_for_llm_hash`, `artifact_hash`, `prev_artifact_hash`, `violation_events`

### Excluded fields

Any methodology naming, `sasi_envelope_attestation` internals (omit or treat as opaque blob per human review), `original_length`, `redacted_length`, `conversation_id`, `llm_profile`, `provider_request_started`, `timestamp_utc` — optional; include only if human review approves

**Note:** Source `TransportAuditRecord` includes additional fields. Public schema intentionally ships the minimal auditor-facing subset. Integrators may store extended engine fields in private stores; strict public export should validate against this schema only.

### PII type categories (generic only)

Allowed `pii_types` values:

`ssn`, `phone`, `email`, `name`, `date_of_birth`, `insurance_id`, `address`, `credit_card`, `account`, `device`, `ip`, `url`, `biometric`, `other`

### Complete structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.saski.dev/transport-audit/v1",
  "title": "SASKI Shadow Transport Audit Record v1",
  "type": "object",
  "required": [
    "record_version",
    "run_id",
    "enforcement_mode",
    "pii_detected",
    "redaction_applied",
    "message_for_llm_hash",
    "artifact_hash"
  ],
  "additionalProperties": false,
  "properties": {
    "record_version": {
      "type": "string",
      "const": "1.0"
    },
    "run_id": {
      "type": "string",
      "minLength": 1
    },
    "enforcement_mode": {
      "type": "string",
      "enum": ["enforce", "shadow", "warn"]
    },
    "jurisdiction_source": {
      "type": ["string", "null"],
      "enum": ["integrator_supplied", "not_provided", "unknown", null],
      "description": "How user jurisdiction was supplied; neutral public enum only"
    },
    "pii_detected": {
      "type": "boolean"
    },
    "pii_types": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "ssn", "phone", "email", "name", "date_of_birth",
          "insurance_id", "address", "credit_card", "account",
          "device", "ip", "url", "biometric", "other"
        ]
      },
      "default": []
    },
    "redaction_applied": {
      "type": "boolean"
    },
    "message_for_llm_hash": {
      "type": "string",
      "pattern": "^[0-9a-f]{32,64}$",
      "description": "Hash of governed LLM egress payload"
    },
    "artifact_hash": {
      "type": "string",
      "pattern": "^[0-9a-f]{32,64}$",
      "description": "Hash of this audit record payload"
    },
    "prev_artifact_hash": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{32,64}$",
      "description": "Previous record hash in per-session chain, or null for first turn"
    },
    "violation_events": {
      "type": "array",
      "description": "Opaque violation summaries",
      "items": {
        "type": "object",
        "additionalProperties": true
      },
      "default": []
    }
  }
}
```

### Example instance (IP-safe)

```json
{
  "record_version": "1.0",
  "run_id": "run_a1b2c3d4",
  "enforcement_mode": "shadow",
  "jurisdiction_source": "integrator_supplied",
  "pii_detected": true,
  "pii_types": ["phone"],
  "redaction_applied": true,
  "message_for_llm_hash": "dddddddddddddddddddddddddddddddd",
  "artifact_hash": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "prev_artifact_hash": null,
  "violation_events": []
}
```

---

## 3. shadow_report_v1.json

### Intent

Eight-section shadow pilot report aggregated from persisted JSONL turn payloads. All analysis has already occurred; this document only describes presentation shapes.

### Top-level structure

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.saski.dev/shadow-report/v1",
  "title": "SASKI Shadow Pilot Report v1",
  "type": "object",
  "required": ["schema_version", "generated_at_utc", "period", "sections"],
  "additionalProperties": false,
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "shadow_report_v1"
    },
    "generated_at_utc": {
      "type": "string",
      "format": "date-time"
    },
    "period": {
      "type": "object",
      "required": ["start_utc", "end_utc"],
      "properties": {
        "start_utc": { "type": "string", "format": "date-time" },
        "end_utc": { "type": "string", "format": "date-time" }
      }
    },
    "sections": {
      "type": "object",
      "required": [
        "pii_phi_detection_summary",
        "compliance_exposure_examples",
        "token_savings_calculation",
        "envelope_evidence_sample",
        "escalation_signal_count",
        "unsafe_flow_documentation",
        "latency_impact_report",
        "recommended_path"
      ],
      "additionalProperties": false,
      "properties": {
        "pii_phi_detection_summary": { "$ref": "#/$defs/pii_phi_detection_summary" },
        "compliance_exposure_examples": { "$ref": "#/$defs/compliance_exposure_examples" },
        "token_savings_calculation": { "$ref": "#/$defs/token_savings_calculation" },
        "envelope_evidence_sample": { "$ref": "#/$defs/envelope_evidence_sample" },
        "escalation_signal_count": { "$ref": "#/$defs/escalation_signal_count" },
        "unsafe_flow_documentation": { "$ref": "#/$defs/unsafe_flow_documentation" },
        "latency_impact_report": { "$ref": "#/$defs/latency_impact_report" },
        "recommended_path": { "$ref": "#/$defs/recommended_path" }
      }
    }
  },
  "$defs": {}
}
```

---

### Section 1: pii_phi_detection_summary

```json
{
  "pii_phi_detection_summary": {
    "section": "pii_phi_detection_summary",
    "period": { "start_utc": "ISO-8601", "end_utc": "ISO-8601" },
    "totals": {
      "turns_processed": 0,
      "turns_with_pii": 0,
      "pii_detection_rate": 0.0
    },
    "by_pii_type": {
      "ssn": 0,
      "phone": 0,
      "email": 0,
      "name": 0,
      "date_of_birth": 0,
      "insurance_id": 0,
      "address": 0,
      "credit_card": 0,
      "other": 0
    },
    "history_redaction": {
      "sessions_with_history_pii": 0,
      "aggregate_pii_types_found": []
    },
    "examples": [
      {
        "turn_index": 0,
        "session_id": "string",
        "pii_types": ["phone"],
        "input_hash": "64-char hex",
        "redaction_applied": true,
        "message_for_llm_hash": "32-64 char hex or null"
      }
    ]
  }
}
```

**IP modifications:** No `original_message_excerpt`, `redacted_message_excerpt`, or `message_for_llm_excerpt`. Examples are hash-only.

---

### Section 2: compliance_exposure_examples

```json
{
  "compliance_exposure_examples": {
    "section": "compliance_exposure_examples",
    "jurisdiction_config": {
      "active_jurisdictions": ["INTEGRATOR_JURISDICTION_CODE"],
      "user_jurisdiction_injected": true
    },
    "examples": [
      {
        "turn_index": 0,
        "session_id": "string",
        "deployment_profile": "integrator_supplied_profile_name",
        "user_jurisdiction": "INTEGRATOR_JURISDICTION_CODE",
        "jurisdiction_source": "integrator_supplied",
        "obligation_label": "COMPLIANCE_OBLIGATION_LABEL",
        "reason_code": "COMPLIANCE_REASON_CODE",
        "compliance_decisions": {
          "pii_category": {
            "action": "block",
            "reason_code": "COMPLIANCE_REASON_CODE"
          }
        },
        "engine_outcome": "block",
        "would_have_blocked_in_enforce": true,
        "enforcement_suppressed_in_shadow": true
      }
    ],
    "aggregate": {
      "turns_with_compliance_decisions": 0,
      "turns_with_jurisdiction_decision": 0,
      "unique_reason_codes": []
    }
  }
}
```

**IP modifications:** No statute names, no real jurisdiction examples like `US-MD`, no `saski_action` — use `engine_outcome`. Placeholder codes only in schema docs.

---

### Section 3: token_savings_calculation

```json
{
  "token_savings_calculation": {
    "section": "token_savings_calculation",
    "prospect_inputs": {
      "avg_tokens_per_session_legacy_system": null,
      "avg_llm_turns_per_session": null,
      "monthly_sessions": null,
      "input_price_per_1m_tokens_usd": null
    },
    "measured_from_shadow": {
      "total_turns": 0,
      "tier_clean_turns": 0,
      "tier_warning_turns": 0,
      "tier_escalation_turns": 0,
      "blocked_llm_turns": 0
    },
    "token_model": {
      "legacy_system_tokens_per_turn": null,
      "governed_system_tokens_per_turn": null,
      "warning_append_tokens": null,
      "regulated_floor_tokens": null
    },
    "savings": {
      "tokens_saved_per_session_estimate": null,
      "monthly_tokens_saved_estimate": null,
      "annual_usd_saved_estimate": null
    }
  }
}
```

**IP modifications:** No hardcoded token constants (120, 40, 70, 400, 2.50). All `token_model` values are `null` in schema default; user supplies via `prospect_inputs`. Tier names are generic (`tier_clean`, `tier_warning`, `tier_escalation`). Aggregator reads pre-computed `governance_tier` from each turn's `engine_summary`; if absent, defaults to `tier_clean`. No private tier classification logic in the public package.

---

### Section 4: envelope_evidence_sample

```json
{
  "envelope_evidence_sample": {
    "section": "envelope_evidence_sample",
    "samples": [
      {
        "turn_index": 0,
        "session_id": "string",
        "mode_tag": "shadow_mode",
        "envelope": {
          "envelope_version": "1.0",
          "run_id": "string",
          "input_hash": "sha256-64",
          "policy_hash": "sha256-64",
          "policy_id": "string",
          "timestamp_utc": "ISO-8601",
          "output_hash": "sha256-64 or null",
          "integrator_signature": null,
          "events": [],
          "invariant_summary": {}
        },
        "transport_audit_record": {
          "record_version": "1.0",
          "run_id": "string",
          "enforcement_mode": "shadow",
          "jurisdiction_source": "integrator_supplied",
          "pii_detected": true,
          "pii_types": ["phone"],
          "redaction_applied": true,
          "message_for_llm_hash": "sha256-32-64",
          "artifact_hash": "sha256-32-64",
          "prev_artifact_hash": null,
          "violation_events": []
        }
      }
    ]
  }
}
```

**IP modifications:** Envelope excludes `controls_snapshot`, `invariant_report` (renamed `invariant_summary`), `reconstruction_artifacts`. Transport record uses public schema only.

---

### Section 5: escalation_signal_count

Renamed from "crisis" to "escalation" in section key to avoid clinical detection terminology in public schema title. Counts use `PublicOutcome` vocabulary.

```json
{
  "escalation_signal_count": {
    "section": "escalation_signal_count",
    "totals": {
      "turns_processed": 0,
      "escalation_turns": 0,
      "escalation_rate": 0.0
    },
    "by_governance_tier": {
      "tier_clean": 0,
      "tier_warning": 0,
      "tier_escalation": 0
    },
    "by_outcome": {
      "allow": 0,
      "warn": 0,
      "block": 0,
      "human_review": 0,
      "crisis_referral": 0,
      "physical_emergency_referral": 0
    },
    "by_risk_band": {
      "low": 0,
      "moderate": 0,
      "elevated": 0,
      "critical": 0
    },
    "examples": [
      {
        "turn_index": 0,
        "session_id": "string",
        "escalation_detected": true,
        "outcome": "crisis_referral",
        "risk_band": "critical",
        "input_hash": "64-char hex",
        "llm_egress_suppressed": true,
        "shadow_actual_llm_response_hash": "64-char hex or null"
      }
    ]
  }
}
```

**IP modifications:** No `is_crisis`, `immediate_988`, `safety_tags`, `show_hotline`, `crisis_summary_excerpt`, `message_for_llm` text. Uses `outcome` and `risk_band` instead of engine `action`/`risk_level`. Examples are hash-only.

---

### Section 6: unsafe_flow_documentation

```json
{
  "unsafe_flow_documentation": {
    "section": "unsafe_flow_documentation",
    "categories": {
      "enforcement_would_block": [],
      "policy_boundary_failure": [],
      "content_sanitization_gap": [],
      "integrator_override": [],
      "manual_review_required": [],
      "other": []
    },
    "examples": [
      {
        "turn_index": 0,
        "session_id": "string",
        "category": "enforcement_would_block",
        "signals": {
          "enforcement_suppressed": true,
          "would_block": true,
          "outcome": "block",
          "human_review_required": false
        },
        "recommended_behavior": "Block LLM egress; serve governed template",
        "observed_llm_response_hash": "64-char hex or null",
        "analyst_note": "Free-text analyst annotation"
      }
    ]
  }
}
```

**IP modifications:** Neutral audit outcome categories only (`enforcement_would_block`, `policy_boundary_failure`, `content_sanitization_gap`, `integrator_override`, `manual_review_required`, `other`). No `adversarial_detected` or `obfuscation_detected` signal fields. No `safety_tags`. The `other` category is a catch-all for integrator-defined findings.

---

### Section 7: latency_impact_report

```json
{
  "latency_impact_report": {
    "section": "latency_impact_report",
    "targets": {
      "integrator_p95_target_ms": null,
      "hosted_p95_target_ms": null
    },
    "aggregate": {
      "turn_count": 0,
      "p50_total_ms": 0.0,
      "p95_total_ms": 0.0,
      "p99_total_ms": 0.0,
      "exceeded_integrator_target_count": 0,
      "exceeded_hosted_target_count": 0
    },
    "phase_timings": {
      "phase_a": { "p50": 0.0, "p95": 0.0, "p99": 0.0 },
      "phase_b": { "p50": 0.0, "p95": 0.0, "p99": 0.0 }
    },
    "outliers": [
      {
        "turn_index": 0,
        "session_id": "string",
        "total_ms": 0.0,
        "phase_timings": {},
        "exceeded_threshold": "integrator_p95"
      }
    ]
  }
}
```

**IP modifications:** No `sdk_p95_target_ms: 50` or `hosted_api_p95_target_ms: 200` defaults. Targets are `null` placeholders. `by_phase` with engine-specific keys replaced by generic `phase_timings` map. Aggregator maps opaque phase keys from turn `latency_breakdown` to `phase_a`, `phase_b`, … or preserves integrator-supplied generic keys.

---

### Section 8: recommended_path

```json
{
  "recommended_path": {
    "section": "recommended_path",
    "recommended_deployment_profile": "integrator_supplied_profile_name",
    "recommended_jurisdiction_config": {
      "active_jurisdictions": ["INTEGRATOR_JURISDICTION_CODE"],
      "require_user_jurisdiction": true
    },
    "expected_production_tier_distribution": {
      "tier_clean_pct": 0.0,
      "tier_warning_pct": 0.0,
      "tier_escalation_pct": 0.0
    },
    "enforce_rollout": {
      "strategy": "all_flows",
      "subset_description": "Integrator-defined cohort description",
      "estimated_days_to_full_enforce": null
    },
    "findings_summary": {
      "pii_risk": "low",
      "escalation_signal_rate": "low",
      "compliance_gaps": [],
      "latency_acceptable": true
    },
    "next_steps": [
      "Integrator-defined next step"
    ]
  }
}
```

**IP modifications:** No `recommended_saski_mode` with real mode names like `mental_health_support`. No `crisis_signal_rate` — renamed `escalation_signal_rate`. No prescriptive next steps referencing engine-specific UI (`immediate_988`). Analyst-authored; aggregator supplies numeric inputs only.

---

## Turn Payload Schema (Input to Aggregator)

The aggregator reads JSONL lines matching this shape. Not shipped as a separate schema file but documented here for build session reference.

```json
{
  "turn_index": 0,
  "timestamp_utc": "ISO-8601",
  "timestamp_ms": 0,
  "session_id": "string",
  "run_id": "string",
  "policy_id": "string or null",
  "policy_hash": "64-char hex",
  "input_hash": "64-char hex",
  "output_hash": "64-char hex or null",
  "response_hash": "64-char hex or null",
  "mode_tag": "shadow_mode",
  "action_label": "PASS_CLEAN",
  "latency_ms": 0.0,
  "model_id": "string or null",
  "provider_id": "string or null",
  "correlation_id": "string or null",
  "outcome_linkage": null,
  "envelope": {},
  "transport_audit_record": {},
  "deployment_decision": {
    "mode": "shadow",
    "enforcement_suppressed": false,
    "effective_should_block": false
  },
  "engine_summary": {
    "outcome": "allow",
    "risk_band": "low",
    "pii_detected": false,
    "pii_types": [],
    "escalation_detected": false,
    "would_block": false,
    "governance_tier": "tier_clean",
    "phase_timings": {}
  }
}
```

`engine_summary` is an optional normalized subset that the integrator or `integrations/saski_sdk.py` adapter writes at persistence time. The aggregator prefers `engine_summary` over reading raw engine metadata. For Section 3 token savings, the aggregator reads `governance_tier` from `engine_summary` only; it does not re-derive tier classification. If `governance_tier` is absent, the aggregator assigns `tier_clean` as the safe default.

---

## Analyzer Output Fields

The `analyze_turn()` function populates these fields in the `AnalysisResult` compatible object:

| Field | Value |
|-------|-------|
| `should_block` | `bool` |
| `action` | `str` — one of `PublicOutcome` values |
| `is_crisis` | `bool` — always `False` in public baseline; phrase match sets `escalation_detected` |
| `pii_detected` | `bool` |
| `pii_types` | list of generic category strings |
| `pipeline_ms` | `float` |
| `processing_time_ms` | `float` |
| `metadata.engine_summary.outcome` | `PublicOutcome` value |
| `metadata.engine_summary.risk_band` | `low`, `moderate`, `elevated`, `critical` |
| `metadata.engine_summary.pii_detected` | `bool` |
| `metadata.engine_summary.pii_types` | list |
| `metadata.engine_summary.escalation_detected` | `bool` |
| `metadata.engine_summary.would_block` | `bool` |
| `metadata.engine_summary.governance_tier` | `tier_clean`, `tier_warning`, `tier_escalation` |
| `metadata.engine_summary.phase_timings` | dict of stage to float ms |
| `metadata.transport_audit_record` | `transport_audit_v1` |
| `metadata.detector_profile` | `baseline-v1` |

**Note:** `is_crisis` is always `False` in the public baseline engine. `escalation_detected` reflects phrase list matches only and must never be marketed as clinical crisis detection.

---

## Schema Validation Rules

1. All hash fields: lowercase hex, length 32 or 64 as specified per field.
2. All timestamps: ISO-8601 UTC with offset or `Z`.
3. No raw text fields in any schema or strict-export turn payload.
4. `enforcement_mode` and `deployment_decision.mode`: `enforce` | `shadow` | `warn` only.
5. `mode_tag`: `saski_on` | `saski_off` | `shadow_mode` | `warn_mode` only.
6. `outcome` and `by_outcome` keys: `PublicOutcome` enum values only.
7. Reject documents containing keys from the IP exclusion lists in SAFE_CONTENT_GUIDE.md.
