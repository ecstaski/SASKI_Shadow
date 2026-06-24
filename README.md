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
| Compliance Exposure | Flags turns that match your own policy rules, and names public US AI laws by jurisdiction and domain from a transparent starter set (see Law Coverage). No built-in statute *enforcement*. |
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

To use the optional licensed-engine adapter 
(`saski_shadow.integrations.saski_sdk`), install 
the extra:

```bash
pip install "saski-shadow[saski-sdk]"
```

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
- Does not ship the full statute enforcement 
  database or any proprietary compliance logic — 
  it matches a transparent starter set of public 
  law facts for exposure awareness only (see 
  Law Coverage below).
- Does not reproduce any proprietary scoring, 
  thresholds, or detection methodology.
- Does not make network calls, download models, 
  or gate on a license.
- Does not itself detect CSAM. CSAM-related 
  compliance signals surface only when an 
  upstream classifier emits the relevant tag for 
  a turn. Without that upstream tag integration, 
  shadow mode will not surface any CSAM 
  compliance signals.

---

## Law Coverage

Shadow mode ships a small, transparent starter 
set of **public US AI law facts** (identifiers, 
jurisdictions, domains, citations, effective 
dates, and plain-language notes). It matches 
those facts to a turn purely by integrator-supplied 
jurisdiction and domain. It does **not** ship the 
enforcement mappings, thresholds, or routing logic 
that the licensed SASKI engine uses.

The exact figures below are derived from the 
starter set itself (`saski_shadow.laws.coverage_summary`) 
and are verified by a test, so they stay accurate 
as the set grows.

**Geographic scope:** shadow mode currently covers 
US state and federal AI laws only — it does not yet 
include EU, UK, or other non-US jurisdictions. If EU 
coverage is added in the future, it will go through 
the same inventory-and-verification process used for 
the US laws here, not be added piecemeal.

### What's included

**73 laws across 36 U.S. state-level and federal jurisdictions**, 
grouped by the per-message signal they relate to:

| Coverage area | Domain | Count |
| --- | --- | --- |
| Conversational AI & companion-chatbot disclosure and safety | `consumer_chatbot` | 16 laws / 14 states |
| AI-generated CSAM | `csam` | 34 laws / 27 states |
| AI employment & hiring discrimination | `employment` | 9 laws / 5 states |
| AI claiming clinical credentials (mental/behavioral health) | `mental_health` | 6 laws / 5 states |
| AI claiming credentials or communicating directly with patients | `healthcare` | 8 laws / 4 states |

The set includes **13 federal (`US`) laws** that apply across every US 
jurisdiction in their domain. In the figures above, federal `US` is 
counted as a single jurisdiction alongside the state-level ones.

Matching is by jurisdiction prefix: a federal `US` entry matches any 
US-prefixed turn (`US-CA`, `US-NY-NYC`, and so on) in the relevant 
domain. So a `US-CA` healthcare turn surfaces both the California 
state healthcare laws and the federal healthcare laws (HIPAA, 
ACA § 1557, and others), while a state-scoped entry like `US-CA` 
matches only `US-CA` turns and narrower.

The healthcare-related entries are a deliberately 
**focused subset**: laws about AI claiming a license 
or credential it doesn't hold, or communicating 
directly with patients as if it were a provider — 
the things a text-only conversational layer can 
actually observe per message.

### What's explicitly NOT included, and why

- **Generic consumer-privacy "automated 
  decision-making" opt-out laws.** These apply to 
  any business processing personal data for 
  automated decisions, not specifically to 
  conversational AI, and there is no per-message 
  signal that distinguishes a chatbot from any 
  other data-processing company.
- **AI healthcare laws governing insurance claims 
  and utilization-review decision systems.** Those 
  regulate a different class of AI system than 
  conversational text and are out of scope for 
  this product.
- **Requirements that are organizational policy 
  rather than per-message checks** (e.g., audit, 
  governance, or record-retention mandates). There 
  is nothing to detect in a single turn.
- **Anything requiring image, audio, or video 
  watermark detection or embedding.** This is a 
  text-only safety middleware.
- **Any law not yet reviewed.** This is a growing 
  starter set, not a claim of exhaustive coverage.

### The core message

Shadow mode is a free, open-source, zero-dependency 
baseline detector for **compliance exposure 
awareness**. It is **not** a substitute for legal 
review, and using it does not mean an integrator's 
AI is safe from violating laws not listed here. The 
licensed SASKI engine provides broader, continuously 
maintained, clinical-grade enforcement.

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
result = analyze_turn(
    user_message,
    session_context={
        "user_jurisdiction": "US-CA",
        # replace with your user's jurisdiction
        # e.g. "US-NY", "US-TX", "US"
        "domain": "consumer_chatbot",
        # one of: consumer_chatbot, csam,
        # employment, mental_health, healthcare
    },
    policy=integrator_policy,
)
# Without user_jurisdiction and domain in
# session_context, the analyzer records no
# compliance context for the turn. Law matching
# in the aggregated report then returns no
# results for that turn.

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

To populate the token-savings section, pass a 
JSON config with your own pricing and token-model 
inputs:

```bash
saski-shadow aggregate \
  --input turns.jsonl \
  --output shadow_report.json \
  --config pricing.json
```

---

## Token savings (how the estimate works)

The token-savings section is an **estimate**, not a 
measurement. It contains **no proprietary SASKI 
constants** — every number is computed by visible 
arithmetic from inputs *you* supply, applied to the 
turn counts observed in your own pilot. Each output 
field stays `null` until the inputs it depends on 
are provided, and the section always reports its 
`basis` (`estimated_from_integrator_inputs` or 
`insufficient_inputs`).

Supply inputs under `prospect_inputs` in the 
`--config` JSON (or via the `prospect_inputs` 
argument to `aggregate_shadow_report`):

```json
{
  "prospect_inputs": {
    "legacy_system_tokens_per_turn": 400,
    "governed_system_tokens_per_turn": 120,
    "warning_append_tokens": 30,
    "regulated_floor_tokens": 200,
    "avg_llm_turns_per_session": 8,
    "monthly_sessions": 100000,
    "input_price_per_1m_tokens_usd": 2.5
  }
}
```

The arithmetic, per LLM turn, is:

```text
governed_total = clean*G + warning*(G + W) + escalation*R
legacy_total   = total_turns * L
saved_total    = max(0, legacy_total - governed_total)
per_session    = (saved_total / total_turns) * avg_llm_turns_per_session
monthly        = per_session * monthly_sessions
annual_usd     = monthly * 12 * input_price_per_1m_tokens_usd / 1_000_000
```

where `L`/`G`/`W`/`R` are your 
`legacy_system_tokens_per_turn`, 
`governed_system_tokens_per_turn`, 
`warning_append_tokens` (defaults to 0), and 
`regulated_floor_tokens` (defaults to `G`). If you 
omit `legacy_system_tokens_per_turn` or 
`governed_system_tokens_per_turn`, the section 
returns all-`null` savings with 
`basis = "insufficient_inputs"`.

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
