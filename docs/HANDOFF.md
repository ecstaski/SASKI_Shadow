# Phase 3 Handoff Document — `saski-shadow`

**Status:** Build complete. Pre-auditor fixes applied. **Not committed. Not pushed.**

**Audience:** Independent IP auditor.

**Build truth:** The shipped package (`saski_shadow/`, `tests/`, `README.md`, `pyproject.toml`) is the source of truth for public naming. Mode tag values are `saski_on` / `saski_off`.

---

## 1. Repository File Inventory

*29 source files. `.pytest_cache/` is pytest runtime output and is excluded.*

### Root

| File | Description |
|------|-------------|
| `README.md` | Public-facing package overview: install, zero-deps claim, quickstart with persistence pattern, CLI, Phase 1→2 upgrade path, schema links, clinical disclaimer. |
| `pyproject.toml` | Hatchling build config, MIT metadata, `dependencies = []`, dev/sasi-sdk optional extras, `saski-shadow` CLI entry point. |

### `docs/`

| File | Description |
|------|-------------|
| `docs/PACKAGE_SPEC.md` | Authoritative build spec: directory layout, public API, behavioral contracts, deployment phases, detector/analyzer requirements. |
| `docs/SAFE_CONTENT_GUIDE.md` | IP-safe extraction rules, forbidden-content lists, per-source-file migration table, adapter allowlist. |
| `docs/SCHEMA_DEFINITIONS.md` | JSON Schema field definitions, turn JSONL shape, section-by-section report schema notes, IP modification callouts. |
| `docs/HANDOFF.md` | This document. |

### `saski_shadow/` — Core package

| File | Description |
|------|-------------|
| `saski_shadow/__init__.py` | Public API re-exports: enums, hashing, types, deployment, evidence, aggregator functions. |
| `saski_shadow/enums.py` | Five public enums: `DeploymentMode`, `ModeTag`, `PublicOutcome`, `ExportActionLabel`, `OutcomeStatus`. |
| `saski_shadow/hashing.py` | Deterministic canonical JSON serialization and SHA-256 helpers (`CanonicalSerializationError`, float quantization). |
| `saski_shadow/types.py` | `AnalysisResult` Protocol and immutable `DeploymentDecision` dataclass. |
| `saski_shadow/deployment.py` | `evaluate_deployment_mode()` — shadow/warn/enforce gating per behavioral contract 5.1. |
| `saski_shadow/evidence.py` | Turn payloads, session bundles, batch manifests, strict export boundary, outcome/label mapping. |

### `saski_shadow/analyzer/`

| File | Description |
|------|-------------|
| `saski_shadow/analyzer/__init__.py` | Exports `analyze_turn()` only. |
| `saski_shadow/analyzer/executor.py` | 8-stage baseline pipeline: normalize → PII → distress → policy → output review → decide → sanitize → evidence. |

### `saski_shadow/detectors/`

| File | Description |
|------|-------------|
| `saski_shadow/detectors/__init__.py` | Four-detector registry (`DETECTORS` dict) and public exports. |
| `saski_shadow/detectors/pii.py` | US-only regex PII detection with Luhn validation and `[REDACTED_*]` placeholders. |
| `saski_shadow/detectors/distress.py` | Conservative public distress phrase matching; module disclaimer; WARN-only behavior documented. |
| `saski_shadow/detectors/policy.py` | Integrator-supplied policy dict evaluator; no built-in statute logic. |
| `saski_shadow/detectors/output_review.py` | Observable output mismatch detection (PII leak, human-escalation claims, boundary phrases). |

### `saski_shadow/aggregate/`

| File | Description |
|------|-------------|
| `saski_shadow/aggregate/__init__.py` | Empty package marker (Phase 1 scaffold). |
| `saski_shadow/aggregate/report.py` | JSONL loader, eight-section `shadow_report_v1` aggregator, CLI `main()`. |

### `saski_shadow/integrations/`

| File | Description |
|------|-------------|
| `saski_shadow/integrations/__init__.py` | Empty package marker (Phase 1 scaffold). |
| `saski_shadow/integrations/saski_sdk.py` | Optional licensed-engine adapter with strict 8-field `engine_summary` allowlist; not imported by core. |

### `saski_shadow/schemas/`

| File | Description |
|------|-------------|
| `saski_shadow/schemas/envelope_v1.json` | Hash-only analysis envelope schema (`integrator_signature` lives here only). |
| `saski_shadow/schemas/transport_audit_v1.json` | Transport-boundary audit record schema with public `jurisdiction_source` enum. |
| `saski_shadow/schemas/shadow_report_v1.json` | Eight-section shadow pilot report schema with disclaimer/upgrade_path fields. |

### `tests/`

| File | Description |
|------|-------------|
| `tests/test_hashing.py` | Canonical serialization, hashing, and error-path tests. |
| `tests/test_deployment.py` | Enforce/shadow/warn gating and `DeploymentDecision` serialization. |
| `tests/test_evidence.py` | Turn payloads, bundles, strict export boundary, outcome/label inference. |
| `tests/test_report.py` | Report structure, tier defaults, PublicOutcome vocab, §2/3/5 messaging, JSONL loader. |
| `tests/test_detectors.py` | PII, distress, policy, output review, and registry tests with synthetic data. |
| `tests/test_analyzer.py` | Pipeline stages, tier assignment, distress→WARN, policy→BLOCK behavior. |

**Test count:** 49 passed.

---

## 2. Human Judgment Calls

### Resolved during build or pre-auditor fixes

| Item | Resolution |
|------|------------|
| Distress alone → `PublicOutcome.WARN`, never `BLOCK` | Approved; documented in `distress.py` disclaimer |
| Policy input is plain Python `dict` only (no YAML in package) | Approved |
| Omit `DEFAULT_POLICY_HASH` and `MinimalAuditRecord` | Approved |
| `jurisdiction_source` schema allows JSON `null` for no-value case | Approved |
| `pyproject.toml` optional extra name `sasi-sdk` (real PyPI package name) | Approved; local adapter file is `saski_sdk.py` |
| Test PII token shapes (`123-45-6789`, `user@example.com`, etc.) | Approved as conventional fakes |
| Empty `aggregate/__init__.py` and `integrations/__init__.py` | Added |
| `saski_shadow/__init__.py` module docstring | Updated to describe baseline shadow observation package |
| Docs: `saski_on`/`saski_off`, `saski_sdk.py`, `SaskiResult` | Updated in all three spec files |

### Remaining items for auditor awareness

| # | Item | Notes |
|---|------|-------|
| 1 | **Distress baseline phrase list** | `_BASELINE_INDICATORS` in `distress.py` contains plain-language crisis expressions (e.g. `"thoughts of suicide"`). Approved as public MH-first-aid-style baseline for the local detector. Lives in production code, not test fixtures. |
| 2 | **Docs: private-repo path references** | `SAFE_CONTENT_GUIDE.md` still references private `sasi_sdk/...` source paths in the migration table. These describe the private extraction source, not public package paths. |
| 3 | **Docs: module import path strings** | `PACKAGE_SPEC.md` still references `integrations.sasi_sdk` in two places; shipped module is `integrations.saski_sdk`. |
| 4 | **Docs: enum member names in spec** | `PACKAGE_SPEC.md` shows `SASI_ON` / `SASI_OFF` enum members; shipped code uses `SASKI_ON` / `SASKI_OFF`. Values are correct (`saski_on` / `saski_off`). |

---

## 3. IP Exclusion Confirmation

Scanned all repo files. Results grouped by scope.

### A. Shippable package surface — `saski_shadow/`, `tests/`, `README.md`

| Exclusion category | Result |
|--------------------|--------|
| MDTSAS or dimension names | **Absent** |
| Semantic anchors or crisis thresholds (as implementation) | **Absent** — word "semantic anchors" appears once in `distress.py` only in negation |
| Symbolic operator names or tag taxonomy | **Absent** |
| Jurisdiction fallback values or statute names (as logic) | **Absent** — "statute" appears only to state there is no built-in statute logic |
| Obfuscation detection thresholds | **Absent** — "obfuscation" appears only in negation |
| Private sasi-sdk module names in code or comments | **Absent** in Python/JSON/schemas/tests/README |
| CEM methodology references or phase numbers | **Absent** |
| Numeric safety/decision threshold values | **Absent** — infrastructure numerics only (timing, percentiles, Luhn bounds, hash quantization, example caps) |
| `EVENT_REGISTRY` or `ALLOWED_EVENT_IDS` | **Absent** |
| `reconstruction_artifacts` or `controls_snapshot` | **Absent** |
| `routing_decision` mapping | **Absent** — "routing decisions" appears in `saski_sdk.py` docstring only in negation |
| `system_prompt_assembly` references | **Absent** |
| Realistic crisis language in test fixtures | **Absent** — tests use synthetic phrases only |
| Realistic PII examples in test fixtures | **Conventional fakes only** — `123-45-6789`, `user@example.com`, `555-000-1111` |
| Jailbreak examples in test fixtures | **Absent** |
| `MODE_FEATURES_MATRIX` references | **Absent** |

**Production-code note:** `saski_shadow/detectors/distress.py` contains a baseline indicator list with plain-language crisis expressions. Approved Phase 4 design choice for the public baseline detector.

### B. `pyproject.toml` — one approved exception

| Item | Result |
|------|--------|
| `sasi-sdk` optional extra and version pin | **Present by design** — real PyPI package name. No `sasi_sdk` imports in Python code. |

### C. `docs/` — IP exclusion reference documents

The three spec documents contain forbidden terms (`MDTSAS`, `reconstruction_artifacts`, `routing_decision`, private `sasi_sdk/...` paths, obfuscation thresholds, etc.) **only as exclusion guidance, migration tables, and "do not include" lists** — not as implemented behavior.

---

## 4. Final Audit Checklist (from build)

| # | Item | Result |
|---|------|--------|
| 1 | `dependencies = []` in pyproject.toml | **PASS** |
| 2 | No import from private engine modules in core | **PASS** |
| 3 | `integrator_signature` in `envelope_v1.json` only | **PASS** |
| 4 | `jurisdiction_source`: integrator_supplied, not_provided, unknown (+ null) | **PASS** |
| 5 | `ExportActionLabel`: exactly four values | **PASS** |
| 6 | Section 6 categories: six neutral values incl. `other` | **PASS** |
| 7 | No realistic content/vendor/threshold in test fixtures | **PASS** |
| 8 | `integrations/saski_sdk.py` not imported in `__init__`/core | **PASS** |
| 9 | `distress.py` module disclaimer present | **PASS** |
| 10 | `policy.py` "coming soon" note present | **PASS** |
| 11 | §2/3/5 upgrade messaging in report output | **PASS** |

---

## 5. Integration Quick Reference (for auditor)

**Critical persistence pattern:**

```python
result = analyze_turn(user_message, policy=integrator_policy)
payload = turn_payload_from_result(result, turn_index=0, session_id="sess_001", mode_tag="shadow_mode")
payload["engine_summary"] = result.metadata["engine_summary"]  # required before persist
payload["transport_audit_record"] = result.metadata["transport_audit_record"]
```

**CLI:**

```bash
saski-shadow aggregate --input turns.jsonl --output shadow_report.json --schema v1
```
