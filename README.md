# saski-shadow

Run a 7-day baseline shadow pilot on your 
own conversation traffic and receive an 
8-section findings report — PII exposure, 
escalation signals, compliance gaps, token 
savings, latency impact, cryptographic 
evidence, unsafe flow documentation, and 
a recommended enforcement path. Everything 
runs inside your own infrastructure. 
Nothing leaves.

> **Baseline observation only.** 
> `saski-shadow` is not clinical crisis 
> detection and must not be used as the 
> sole safety layer for any regulated 
> deployment. For clinical-grade accuracy 
> add the licensed SASKI engine — see 
> Phase 2 below.

---

## What you get

**Phase 1 — saski-shadow only**

Install one package. No account. No network 
calls. No licensed engine required. The 
baseline detector runs locally inside your 
own infrastructure on your real conversation 
traffic and produces a complete 8-section 
shadow report.

Report sections and what they honestly promise:

| Section | What the baseline delivers |
|---------|---------------------------|
| PII and PHI Detection | Counts and redacts obvious US identifier patterns — SSN, phone, email, credit card, date of birth, insurance ID, address, IP. Not HIPAA Safe Harbor complete. |
| Compliance Exposure | Flags turns that match your own policy rules. No built-in statute enforcement. A built-in US AI law database is coming soon. |
| Token Savings | Arithmetic estimate from your actual tier counts and integrator-supplied pricing inputs. |
| Cryptographic Evidence | Full structural accuracy — deterministic hashes, artifact chain, schema-valid envelope. This is the strongest section. |
| Escalation Signals | Counts conservative public distress phrase matches. Not clinical crisis detection. |
| Unsafe Flow Documentation | Documents observable mismatches between detection signals and actual LLM behavior. |
| Latency Impact | Accurate local phase timings at p50, p95, p99. |
| Recommended Path | Template guidance from aggregate findings. Analyst-authored. |

**Phase 2 — saski-shadow + licensed SASKI engine**

Add the licensed SASKI engine to the same 
VPC. The optional adapter maps its output 
onto the same AnalysisResult protocol. The 
JSONL pipeline, schemas, and report format 
stay identical — no re-architecture required.

What the licensed engine adds:

- Clinical-grade safety detection across 
  conversation history
- HIPAA Safe Harbor complete PII redaction 
  across all 18 identifier types
- Jurisdiction statute enforcement for active 
  US state and federal AI laws
- Production safety routing with enforcement-
  grade blocking and escalation
- Advanced threat and evasion detection

The same shadow report. Dramatically more 
accurate results. Same integration. One 
configuration change.

---

## Installation

```bash
pip install saski-shadow
```

**Zero runtime dependencies.** The core 
package installs nothing beyond the Python 
standard library. Optional extras exist only 
for development and the licensed engine adapter.

---

## What it does

- Runs a local transparent baseline detection 
  pass on each user message — PII, distress 
  indicators, integrator policy rules, 
  output review.
- Converts results into deterministic hash-only 
  turn payloads — no raw message text in your 
  store.
- Gates an LLM in shadow, warn, or enforce mode.
- Builds integrity-checked session evidence 
  bundles.
- Aggregates persisted turns into a 
  shadow_report_v1 pilot report.

## What it does not do

- Does not perform clinical safety enforcement 
  or crisis detection.
- Does not ship a statute or jurisdiction law 
  database — compliance is evaluated against 
  your own policy rules only.
- Does not reproduce any proprietary scoring, 
  thresholds, or detection methodology.
- Does not make network calls, download models, 
  or gate on a license.

---

## Quickstart

### The critical persistence step

When you persist a turn, build the hash-only 
payload and then attach the full engine_summary 
from the analyzer result before writing it. 
The aggregator relies on that block for tier, 
escalation, and timing fidelity in the report.

```python
import json

from saski_shadow import (
    turn_payload_from_result,
    evaluate_deployment_mode,
    DeploymentMode,
)
from saski_shadow.analyzer import analyze_turn

# 1. Run the local baseline analyzer.
result = analyze_turn(user_message, policy=integrator_policy)

# 2. Build a hash-only turn payload.
payload = turn_payload_from_result(
    result,
    turn_index=0,
    session_id="sess_001",
    mode_tag="shadow_mode",
)

# 3. CRITICAL: attach engine_summary before 
#    persisting. This is required for full 
#    report fidelity.
payload["engine_summary"] = result.metadata["engine_summary"]

# 4. Optionally attach transport audit record.
payload["transport_audit_record"] = (
    result.metadata["transport_audit_record"]
)

# 5. Persist to your turn store.
with open("turns.jsonl", "a", encoding="utf-8") as store:
    store.write(json.dumps(payload) + "\n")

# 6. Apply deployment gating.
#    In shadow mode effective_should_block 
#    is always False — nothing blocks.
decision = evaluate_deployment_mode(
    result, mode=DeploymentMode.SHADOW
)
```

### Bringing your own results

You are not required to use the baseline 
analyzer. Any object satisfying the 
AnalysisResult protocol works with 
turn_payload_from_result, build_evidence_bundle, 
and the aggregator. If you use the licensed 
SASKI engine, the optional adapter at 
saski_shadow.integrations.saski_sdk maps its 
output onto the same protocol automatically.

---

## CLI

```bash
saski-shadow aggregate \
  --input turns.jsonl \
  --output shadow_report.json \
  --schema v1
```

---

## Schemas

Public JSON Schemas ship inside the package:

- saski_shadow/schemas/envelope_v1.json — 
  hash-only analysis envelope
- saski_shadow/schemas/transport_audit_v1.json — 
  transport-boundary audit record
- saski_shadow/schemas/shadow_report_v1.json — 
  eight-section shadow pilot report

All hash fields are lowercase hex. All 
timestamps are ISO-8601 UTC. No schema or 
strict-export turn payload contains raw 
message text.

---

## License

MIT — SASKI Institute PBC
