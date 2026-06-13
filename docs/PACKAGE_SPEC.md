# saski-shadow — Package Specification

**Version:** 0.1.0-draft  
**Audience:** Build agents implementing the standalone public repository  
**Status:** IP-reviewed specification — do not add analysis engine code

---

## 1. Package Purpose

`saski-shadow` is a standalone local package that runs a transparent baseline detection engine on conversation traffic inside the integrator's own infrastructure, then validates, aggregates, and packages the results into an 8-section shadow pilot report. It requires no SASKI account, no external API calls, and no licensed engine for Phase 1 shadow pilots.

`saski-shadow` does **NOT** perform clinical safety enforcement. It does not reproduce SASKI crisis detection thresholds, MDTSAS scoring, jurisdiction statute compilation, symbolic operators, or proprietary PII redaction logic. The licensed `sasi-sdk` may be added later in the same VPC to upgrade report accuracy without changing the integration architecture.

---

## 2. Directory and File Structure

```
saski-shadow/
  pyproject.toml
  README.md
  saski_shadow/
    __init__.py
    deployment.py
    evidence.py
    hashing.py
    types.py
    enums.py
    analyzer/
      __init__.py
      executor.py
    detectors/
      __init__.py
      pii.py
      distress.py
      policy.py
      output_review.py
    schemas/
      envelope_v1.json
      transport_audit_v1.json
      shadow_report_v1.json
    aggregate/
      report.py
    integrations/
      saski_sdk.py
  tests/
    test_deployment.py
    test_evidence.py
    test_hashing.py
    test_report.py
    test_analyzer.py
    test_detectors.py
```

| File | Contents |
|------|----------|
| `pyproject.toml` | Package metadata, zero runtime dependencies, dev test deps, CLI entry point |
| `README.md` | Public install guide, quickstart for shadow gating + turn persistence + report aggregation |
| `saski_shadow/__init__.py` | Public API re-exports only; no private module paths |
| `saski_shadow/deployment.py` | `DeploymentMode`, `DeploymentDecision`, `evaluate_deployment_mode()` |
| `saski_shadow/evidence.py` | Turn payloads, evidence bundles, batch manifests, outcome updates, strict export boundary |
| `saski_shadow/hashing.py` | Canonical serialization, SHA-256 helpers, input/output/payload hashing |
| `saski_shadow/types.py` | `AnalysisResult` protocol, minimal audit record shape, type aliases |
| `saski_shadow/enums.py` | `DeploymentMode`, `ModeTag`, `PublicOutcome`, `ExportActionLabel`, `OutcomeStatus` |
| `saski_shadow/analyzer/__init__.py` | Public entry point for `analyze_turn()` |
| `saski_shadow/analyzer/executor.py` | Ordered pipeline runner: normalize, detect, decide, sanitize, hash, build evidence |
| `saski_shadow/detectors/__init__.py` | Detector registry |
| `saski_shadow/detectors/pii.py` | US-only regex PII detection for `ssn`, `phone`, `email`, `credit_card`, `date_of_birth`, `insurance_id`, `address`, `ip`. No SASKI private patterns. |
| `saski_shadow/detectors/distress.py` | Conservative public distress phrase list. Clearly labeled not clinical crisis detection. No SASKI thresholds or anchors. |
| `saski_shadow/detectors/policy.py` | Integrator policy YAML evaluator. Reads customer-supplied rules only. |
| `saski_shadow/detectors/output_review.py` | Observable output mismatch detection. No private adversarial or drift logic. |
| `saski_shadow/schemas/envelope_v1.json` | Public envelope JSON Schema (hash-only, opaque events) |
| `saski_shadow/schemas/transport_audit_v1.json` | Public transport audit JSON Schema (field names/types only) |
| `saski_shadow/schemas/shadow_report_v1.json` | Eight-section shadow pilot report JSON Schema |
| `saski_shadow/aggregate/report.py` | JSONL → `shadow_report_v1` aggregator and CLI backing logic |
| `saski_shadow/integrations/saski_sdk.py` | Optional adapter when `sasi-sdk` is installed; maps engine result → `AnalysisResult` |
| `tests/test_deployment.py` | Deployment gating unit tests with stub results |
| `tests/test_evidence.py` | Turn payload, bundle integrity, strict boundary tests |
| `tests/test_hashing.py` | Hash normalization and canonical serialization tests |
| `tests/test_report.py` | Report aggregation tests over synthetic JSONL fixtures |

---

## 3. pyproject.toml Specification

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "saski-shadow"
version = "0.1.0"
description = "Shadow-mode evidence validation, aggregation, and export for SASKI integrations"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
  { name = "MyTrusted.AI", email = "sdk@mytrusted.ai" }
]
keywords = ["ai-safety", "shadow-mode", "audit", "evidence", "compliance"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.9",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
dependencies = []

[project.optional-dependencies]
dev = [
  "pytest>=7.0",
  "black>=23.0",
  "ruff>=0.1.0",
]
sasi-sdk = [
  "sasi-sdk>=1.6.4",
]

[project.scripts]
saski-shadow = "saski_shadow.aggregate.report:main"

[project.urls]
Homepage = "https://mytrusted.ai"
Repository = "https://github.com/mytrustedai/saski-shadow"
Documentation = "https://github.com/mytrustedai/saski-shadow#readme"

[tool.hatch.build.targets.wheel]
packages = ["saski_shadow"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]

[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]
```

**Notes:**

- `dependencies = []` — zero runtime dependencies; stdlib only.
- `sasi-sdk` is an **optional** extra for `integrations/saski_sdk.py`; the core package must work without it.
- CLI entry point: `saski-shadow aggregate --input turns.jsonl --output report.json`.

---

## 4. Public API Surface

### 4.1 Enums (`saski_shadow.enums`)

```python
class DeploymentMode(str, Enum):
    ENFORCE = "enforce"
    SHADOW = "shadow"
    WARN = "warn"

class ModeTag(str, Enum):
    SASI_ON = "saski_on"
    SASI_OFF = "saski_off"
    SHADOW_MODE = "shadow_mode"
    WARN_MODE = "warn_mode"

class PublicOutcome(str, Enum):
    """Integrator-facing outcome vocabulary."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"
    CRISIS_REFERRAL = "crisis_referral"
    PHYSICAL_EMERGENCY_REFERRAL = "physical_emergency_referral"

class ExportActionLabel(str, Enum):
    """Research export taxonomy for turn payloads."""
    PASS_CLEAN = "PASS_CLEAN"
    BLOCK_SAFETY = "BLOCK_SAFETY"
    REWRITE_SENSITIVE = "REWRITE_SENSITIVE"
    PASS_WITH_MONITOR = "PASS_WITH_MONITOR"

class OutcomeStatus(str, Enum):
    RESOLVED = "Resolved"
    HARM = "Harm"
    UNKNOWN = "Unknown"
```

### 4.2 Types (`saski_shadow.types`)

```python
class AnalysisResult(Protocol):
    """Duck-typed interface for objects produced by a safety engine."""
    should_block: bool
    action: Any  # engine-specific; mapped internally to PublicOutcome / ExportActionLabel
    is_crisis: bool
    pii_detected: bool
    envelope: Any | None
    policy_id: str | None
    policy_hash: str | None
    pipeline_ms: float
    processing_time_ms: float
    model_id: str | None
    provider_id: str | None
    metadata: dict[str, Any] | None

    def get_audit_record(self) -> dict[str, Any]: ...

@dataclass(frozen=True)
class DeploymentDecision:
    mode: str
    original_should_block: bool
    effective_should_block: bool
    enforcement_suppressed: bool
    warn_user: bool
    reason: str

    def to_dict(self) -> dict[str, Any]: ...
```

### 4.3 Deployment (`saski_shadow.deployment`)

```python
def evaluate_deployment_mode(
    result: AnalysisResult,
    mode: DeploymentMode | str = DeploymentMode.ENFORCE,
) -> DeploymentDecision:
    """Convert engine should_block into integrator action policy for shadow/warn/enforce."""
```

### 4.4 Hashing (`saski_shadow.hashing`)

```python
class CanonicalSerializationError(Exception):
    """Raised when canonical serialization fails (e.g. NaN/Infinity)."""

def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON string: sorted dict keys, stable float quantization."""

def canonical_bytes(obj: Any) -> bytes:
    """UTF-8 bytes of canonical_dumps(obj)."""

def sha256_hex(data: bytes) -> str:
    """SHA-256 lowercase hex digest."""

def hash_message(text: str) -> str:
    """Input hash: NFKD-normalized, stripped text → SHA-256 hex."""

def normalize_output_text_for_hashing(text: str) -> str:
    """Strip leading/trailing whitespace; preserve case and internal spacing."""

def compute_output_hash(output_text: str) -> str:
    """SHA-256 of normalized output text."""

def compute_llm_payload_hash(
    message_for_llm: str,
    history_for_llm: list[dict[str, Any]] | None = None,
    system_prompt_for_llm: str | None = None,
) -> str:
    """Canonical SHA-256 of governed LLM egress payload (hashes only in exports)."""

def artifact_hash(payload: dict[str, Any]) -> str:
    """Stable 32-char hex prefix of canonical payload hash for transport audit chaining."""
```

### 4.5 Evidence (`saski_shadow.evidence`)

```python
RAW_TEXT_KEYS: frozenset[str]  # Keys rejected in strict export boundary

def turn_payload_from_result(
    result: AnalysisResult,
    *,
    turn_index: int,
    session_id: str,
    timestamp_utc: str | None = None,
    model_id: str | None = None,
    provider_id: str | None = None,
    response_hash: str | None = None,
    output_hash: str | None = None,
    llm_response_text: str | None = None,
    correlation_id: str | None = None,
    mode_tag: str = "saski_on",
    action_label: str | None = None,
    outcome_linkage: dict[str, Any] | None = None,
    timestamp_ms: int | None = None,
) -> dict[str, Any]:
    """Build one hash-only turn dict from an AnalysisResult."""

def build_evidence_bundle(
    session_id: str,
    turns: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    *,
    strict_export_boundary: bool = False,
) -> dict[str, Any]:
    """Ordered session bundle with integrity_checksum."""

def generate_batch_manifest(
    jsonl_paths: Iterable[str],
    manifest_path: str | None = None,
) -> dict[str, Any]:
    """Per-file and batch-root SHA-256 manifest."""

def record_research_event(
    input_text: str,
    output_text: str,
    mode_tag: str,
    session_id: str,
) -> dict[str, Any]:
    """One-turn strict-boundary bundle without raw text."""

def update_bundle_outcome(
    run_id: str,
    status: str,
    corrective_action_taken: bool,
    latency_ms: float | None = None,
) -> dict[str, Any]:
    """Async outcome update payload keyed by run_id."""

def map_public_outcome(result: AnalysisResult) -> PublicOutcome:
    """Map engine action + flags to approved public outcome vocabulary."""

def infer_export_action_label(result: AnalysisResult) -> str:
    """Map engine signals to ExportActionLabel without exposing engine internals."""
```

### 4.6 Aggregate (`saski_shadow.aggregate.report`)

```python
def aggregate_shadow_report(
    turns: list[dict[str, Any]],
    *,
    period_start_utc: str | None = None,
    period_end_utc: str | None = None,
    prospect_inputs: dict[str, Any] | None = None,
    latency_targets: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Produce shadow_report_v1 JSON from persisted turn payloads."""

def load_turns_jsonl(path: str) -> list[dict[str, Any]]:
    """Load one JSON object per line from integrator turn store."""

def main(argv: list[str] | None = None) -> int:
    """CLI: saski-shadow aggregate --input PATH --output PATH [--schema v1]."""
```

### 4.7 Integrations (`saski_shadow.integrations.sasi_sdk`)

```python
def adapt_engine_result(result: Any) -> AnalysisResult:
    """Wrap a licensed sasi-sdk SaskiResult as AnalysisResult (optional extra only)."""

def turn_payload_from_engine(
    result: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Convenience: adapt + turn_payload_from_result in one call."""
```

### 4.8 Package exports (`saski_shadow.__init__.__all__`)

Export only:

- `DeploymentMode`, `DeploymentDecision`, `evaluate_deployment_mode`
- `AnalysisResult`, `PublicOutcome`, `ExportActionLabel`, `ModeTag`, `OutcomeStatus`
- `CanonicalSerializationError`
- `canonical_dumps`, `canonical_bytes`, `sha256_hex`, `hash_message`
- `normalize_output_text_for_hashing`, `compute_output_hash`, `compute_llm_payload_hash`, `artifact_hash`
- `turn_payload_from_result`, `build_evidence_bundle`, `generate_batch_manifest`
- `record_research_event`, `update_bundle_outcome`
- `aggregate_shadow_report`, `load_turns_jsonl`

Do **not** export `integrations.sasi_sdk` from top-level `__init__`; document it as optional import path.

### 4.9 Analyzer (`saski_shadow.analyzer`)

```python
def analyze_turn(
    message: str,
    session_context: dict | None = None,
    policy: dict | None = None,
) -> AnalysisResult:
    """Runs the ordered public baseline pipeline on a single user message.

    Returns an AnalysisResult compatible with all existing evidence and
    deployment functions.

    Pipeline stages in order:
    1. normalize_input
    2. detect_pii
    3. detect_distress
    4. evaluate_policy
    5. review_output
    6. decide_outcome
    7. sanitize_egress
    8. build_evidence fields

    Pipeline returns timing per stage in phase_timings. No stage imports from
    private sasi-sdk modules.
    """
```

---

## 5. Behavioral Contracts

### 5.1 Deployment gating

| Mode | `effective_should_block` | `enforcement_suppressed` | `warn_user` |
|------|--------------------------|--------------------------|-------------|
| `enforce` | `result.should_block` | `False` | `False` |
| `shadow` | `False` | `result.should_block` | `False` |
| `warn` | `False` | `result.should_block` | `result.should_block` |

### 5.2 Strict export boundary

When `strict_export_boundary=True`, reject turns containing keys in `RAW_TEXT_KEYS`:

`raw_prompt`, `raw_response`, `message_for_llm`, `history_for_llm`, `system_prompt_for_llm`, `prompt`, `completion`

Required per turn: `run_id`, `session_id`, `policy_hash`, `input_hash`, `output_hash`, `mode_tag`, `timestamp_ms`, `action_label`.

### 5.3 Public outcome mapping (engine action → PublicOutcome)

Implementers map engine `action` string values using this table. Do not document engine-specific action strings in public README.

| Engine action signal (opaque) | PublicOutcome |
|-------------------------------|---------------|
| continue, empathy | `allow` |
| monitor, resources | `warn` |
| block | `block` |
| human_review | `human_review` |
| crisis referral action | `crisis_referral` |
| physical emergency referral action | `physical_emergency_referral` |

### 5.4 Export action label inference

| Condition on AnalysisResult | ExportActionLabel |
|-----------------------------|-------------------|
| `should_block` is true | `BLOCK_SAFETY` |
| monitoring/warn action | `PASS_WITH_MONITOR` |
| sanitization detected (PII rewrite, message transform) | `REWRITE_SENSITIVE` |
| otherwise | `PASS_CLEAN` |

Sanitization detection uses only: `pii_detected`, message length delta between redacted and egress fields — no obfuscation or crisis internals.

### 5.5 Public governance tier assignment

| `governance_tier` | Condition |
|-------------------|-----------|
| `tier_clean` | No signals detected |
| `tier_warning` | Any `pii_detected` or `outcome` is `warn` |
| `tier_escalation` | `would_block` is true or `escalation_detected` is true or `outcome` is `crisis_referral` or `physical_emergency_referral` |

These are the only tier rules in the public package. Do not import or replicate private tier logic.

---

## 6. Non-Goals

The public package must **not** include:

- Safety analysis pipeline
- Crisis, PII, or compliance detection
- Mode configuration tables
- Envelope population logic (only schema validation + passthrough of pre-built envelope dicts)
- Transport audit record **creation** (only schema + passthrough from `metadata["transport_audit_record"]`)
- Network calls, model downloads, or license gates

### 6.1 Per-section accuracy promise

| Section | Accuracy promise |
|---------|------------------|
| **1. PII** | High structural accuracy for obvious US patterns. Not HIPAA Safe Harbor complete. Label as baseline detector. |
| **2. Compliance** | Policy-wiring accuracy only. Customer-supplied rules. Not statute enforcement. Add disclaimer. A built-in US AI law database is coming soon and will automatically populate this section from active federal and state legislation. |
| **3. Token savings** | Arithmetic accuracy from integrator inputs and measured tier counts. Not production SASKI economics. Add disclaimer. |
| **4. Evidence** | Full structural accuracy. This is the strongest public section. |
| **5. Escalation** | Phrase-list accuracy only. Not clinical crisis detection. Must include disclaimer in report and README. |
| **6. Unsafe flows** | Deployment-behavior accuracy from observable signals only. No private detector categories. |
| **7. Latency** | Full structural accuracy for local phase timings. |
| **8. Recommended path** | Template guidance only. Analyst-authored. Not SASKI clinical recommendation. |

---

## 7. Minimum Integrator Flow

```python
from saski_shadow import (
    evaluate_deployment_mode,
    turn_payload_from_result,
    build_evidence_bundle,
    DeploymentMode,
)

# 1. Call licensed engine (separate package)
result = engine.analyze(user_message)

# 2. Apply deployment gating
decision = evaluate_deployment_mode(result, mode=DeploymentMode.SHADOW)

# 3. Persist hash-only turn
payload = turn_payload_from_result(
    result,
    turn_index=0,
    session_id="sess_001",
    mode_tag="shadow_mode",
    llm_response_text=assistant_text,
)

# 4. Export session bundle
bundle = build_evidence_bundle("sess_001", [payload], strict_export_boundary=True)

# 5. Gate LLM on decision.effective_should_block (False in shadow)
```

```bash
# Aggregate pilot report from JSONL store
saski-shadow aggregate --input turns.jsonl --output shadow_report.json --schema v1
```

---

## 8. Phase 1 and Phase 2 deployment

**Phase 1:** Install `saski-shadow` only.

- Baseline detection engine runs locally.
- No SASKI account required.
- Report sections carry baseline disclaimers.

**Phase 2:** Add licensed `sasi-sdk` in same VPC.

- Same JSONL pipeline and report schema.
- Adapter in `integrations/saski_sdk.py` replaces baseline analyzer as result source.
- Report upgrades to clinical accuracy.
- No integration re-architecture required.
- Different `policy_id` and report banner distinguish Phase 1 from Phase 2 reports.
