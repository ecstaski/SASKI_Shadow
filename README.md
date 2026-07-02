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

**Integrating into your chatbot?** See **[INTEGRATION.md](INTEGRATION.md)**
for hook points, persistence, reports, and pilot workflow.

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
| Compliance Exposure | Flags turns that match your own policy rules, and names public US AI laws by jurisdiction and domain when you supply that metadata (see [INTEGRATION.md](INTEGRATION.md#required-metadata-for-compliance-matching)). No built-in statute *enforcement*. |
| Token Savings | Arithmetic estimate of tokens saved from your observed tier counts and two integrator-supplied token inputs. Reports tokens only — never a dollar figure. |
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
  it names public law facts for exposure awareness 
  only when you supply jurisdiction and domain 
  metadata (see [INTEGRATION.md](INTEGRATION.md#required-metadata-for-compliance-matching)).
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

## Data stays on your infrastructure

`saski-shadow` makes **no outbound network calls** at runtime. There is no
account, API key, telemetry endpoint, or automatic upload to SASKI Institute.
Shadow turn stores (`*.jsonl`), aggregated reports (`report.json`), and HTML
reports are written only to paths **you** configure on your own machines.

Persisted turn records from `result_to_jsonl_turn()` are **hash-only** by
design — no raw user or assistant message text in the default JSONL pipeline.
You control retention, access, and whether any file ever leaves your
environment.

**We cannot see your shadow pilot traffic** unless you choose to share
artifacts with us separately.

### Optional feedback (voluntary)

If you are comfortable doing so, you may email aggregate pilot artifacts to
[shadowreport@saski.io](mailto:shadowreport@saski.io) to help us improve shadow mode and
the licensed SASKI product. This is **entirely optional** and never required to
use the package.

For integration questions or issues, contact
[support@saski.io](mailto:support@saski.io).

Helpful to share:

- Aggregated `report.json` or `report.html` from a completed pilot
- Schema version (`shadow_report_v1`) and a short integration note (jurisdiction,
  domains, approximate turn count)

These outputs contain counts, hashes, and compliance metadata — not message
contents. Default `shadow_turns.jsonl` from this package is also hash-only, but
only share it if you have verified your integration did not add raw text fields.

Please **do not** email raw conversation logs, unredacted user content, or
`pricing.json` (your local token-cost inputs). If you need a formal data-sharing
arrangement, contact us first.

We use voluntary submissions only for product improvement unless you ask for
follow-up.

---

## Compliance exposure

Section 2 of the shadow report names **public US AI law facts** when you supply
`user_jurisdiction` and `domain`/`domains` on each turn. Matching is by
jurisdiction prefix and domain intersection only — not inferred from message
content. This is exposure awareness, not statute enforcement or legal advice.

Required metadata, valid domain tags, and CSAM upstream wiring are documented in
**[INTEGRATION.md](INTEGRATION.md)**.

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
