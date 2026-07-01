# Integrating saski-shadow into your chatbot

This guide is for application developers wiring shadow mode into a
conversational AI product (sandbox or production pilot). It assumes Python 3
on your backend. For package overview and law coverage, see [README.md](README.md).

Shadow mode **observes** traffic only. It does not block, modify, or suppress
LLM output. Use `DeploymentMode.SHADOW` during a pilot so user-facing behavior
stays unchanged while you collect findings.

---

## End-to-end flow

```text
User message
    │
    ▼
analyze_turn()          ← baseline detection on user text (+ optional context)
    │
    ▼
Your LLM call           ← unchanged in shadow mode
    │
    ▼
analyze_turn() again    ← optional but recommended: pass assistant_output
    │                     in session_context for output-review signals
    ▼
result_to_jsonl_turn()  ← build aggregator-ready turn record
    │
    ▼
Persist turn            ← JSONL file, database row, object store, etc.
    │
    ▼
(When you choose)       ← no built-in scheduler
aggregate_shadow_report() + generate_html_report()
```

There is **no automatic report trigger** in the package. You run aggregation
when your pilot ends, on a schedule you define (cron, admin button, turn-count
threshold), or on demand.

---

## Recommended per-turn integration

Use `result_to_jsonl_turn()` — it carries the full `engine_summary` the report
aggregator needs. The lower-level `turn_payload_from_result()` evidence helper
emits a slimmer summary and will produce incomplete tier, escalation, and
latency sections unless you attach the full block yourself.

```python
import json

from saski_shadow import (
    DeploymentMode,
    aggregate_shadow_report,
    evaluate_deployment_mode,
    result_to_jsonl_turn,
)
from saski_shadow.analyzer import analyze_turn
from saski_shadow.reporting import generate_html_report

def handle_chat_turn(
    user_message: str,
    assistant_reply: str,
    *,
    turn_index: int,
    session_id: str,
    user_jurisdiction: str,
    domains: list[str],
    integrator_policy: dict | None = None,
    mode: str | None = None,
) -> None:
    # Analyze after you have both sides of the turn for richest signals.
    result = analyze_turn(
        user_message,
        session_context={
            "user_jurisdiction": user_jurisdiction,
            "domains": domains,
            "assistant_output": assistant_reply,
        },
        policy=integrator_policy,
        mode=mode,
    )

    # Shadow mode: observe only — never block the LLM path.
    decision = evaluate_deployment_mode(result, mode=DeploymentMode.SHADOW)
    assert decision.effective_should_block is False

    turn = result_to_jsonl_turn(
        result,
        session_id=session_id,
        turn_index=turn_index,
        provider_id="your_provider_id",
    )

    with open("turns.jsonl", "a", encoding="utf-8") as store:
        store.write(json.dumps(turn) + "\n")
```

### Required metadata for compliance matching

Law exposure in section 2 of the report is keyed on **integrator-supplied**
jurisdiction and domain — not inferred from message text.

| Field | Example | Notes |
| --- | --- | --- |
| `user_jurisdiction` | `"US-CA"`, `"US-NY-NYC"`, `"US"` | US-prefixed codes only today |
| `domain` or `domains` | `"mental_health"` or `["consumer_chatbot", "mental_health"]` | `domains` list preferred for multi-domain products |

Valid domain tags: `consumer_chatbot`, `csam`, `employment`, `mental_health`,
`healthcare`.

If either jurisdiction or domain is missing, compliance matching returns no
laws for that turn (not an error — the report states plainly that metadata
was absent).

### Regulated `mode` tag

Pass `mode` when the conversation is child- or patient-facing:

- `"child"`, `"patient"`, `"therapist"` — affects governance tier and token-savings
  regulated-mode floor in the report
- Omit or use other values for general assistant traffic

### `assistant_output`

Pass the model's reply in `session_context["assistant_output"]` so output
review can detect sanitization gaps and policy boundary failures in section 6.
Without it, unsafe-flow documentation is limited to input-side signals.

---

## Persistence

The package does not ship a turn database. Common patterns:

| Backend | Approach |
| --- | --- |
| **JSONL file** | Append one JSON object per line (examples in this guide) |
| **SQL** | Store the turn dict as a JSON column; export to JSONL before aggregation |
| **Object store** | One object per turn or daily JSONL shard |

Turn records are **hash-only** — no raw user or assistant message text in the
persisted payload. Retention and access control are your responsibility.

---

## Generating reports

### JSON (CLI)

```bash
saski-shadow aggregate \
  --input turns.jsonl \
  --output shadow_report.json \
  --config pricing.json
```

Copy `pricing.example.json` to `pricing.json` locally for token-savings inputs.
`pricing.json` should not be committed (it is gitignored in this repo's dev
layout).

### JSON + HTML (programmatic)

The CLI writes JSON only. For a customer-facing HTML report:

```python
from saski_shadow import aggregate_shadow_report, load_turns_jsonl
from saski_shadow.reporting import generate_html_report

turns = load_turns_jsonl("turns.jsonl")
report = aggregate_shadow_report(
    turns,
    prospect_inputs={
        "legacy_system_prompt_tokens": 450,
        "lean_product_prompt_tokens": 103,
    },
)
generate_html_report(report, "shadow_report.html")
```

Filter by date range or session before aggregating by slicing the turn list or
using `period_start_utc` / `period_end_utc` on `aggregate_shadow_report()`.

### CLI (JSON only)

```bash
saski-shadow aggregate \
  --input turns.jsonl \
  --output shadow_report.json \
  --schema v1
```

Pass `--config pricing.json` (see below) to populate the token-savings section.

---

## Token savings (how the estimate works)

The token-savings section is an **estimate**, not a measurement. It contains
**no proprietary SASKI constants** — every number is computed by visible
arithmetic from inputs *you* supply, applied to the turn counts observed in
your pilot. Each output field stays `null` until the inputs it depends on are
provided, and the section always reports its `basis`
(`estimated_from_integrator_inputs` or `insufficient_inputs`).

Pass inputs under `prospect_inputs` (via `aggregate_shadow_report()`, the
`saski-shadow aggregate --config` flag, or `pricing.json` — see
`pricing.example.json`):

```json
{
  "prospect_inputs": {
    "legacy_system_prompt_tokens": 450,
    "lean_product_prompt_tokens": 103
  }
}
```

- `legacy_system_prompt_tokens` (L) — your current ungoverned system-prompt
  cost per LLM turn.
- `lean_product_prompt_tokens` (P) — the governed lean product-prompt cost per
  turn.

Per-turn arithmetic (keyed on governance tier and regulated `mode`):

```text
floor   = regulated_mode_floor_tokens if mode is regulated else 0
Tier 1  saved = max(0, L - (P + floor))
Tier 2  saved = max(0, L - (P + floor + warning_append))
Tier 3  saved = L            # enforce mode would not call the LLM at all
tokens_saved  = sum of per-turn saved across observed turns
```

Optional overrides: `regulated_mode_floor_tokens` (default **85**),
`warning_append_tokens` (default **50**). Omit either required input and all
savings fields return `null` with `basis = "insufficient_inputs"`.

**No dollar figure is ever computed.** Multiply `tokens_saved` by your own
input cost per token:
`dollar_savings = tokens_saved × (your cost per token)`.

---

## Pilot workflow

A typical **7-day shadow pilot** (recommended duration, not enforced):

1. Deploy shadow mode on real or sandbox traffic.
2. Persist every turn with jurisdiction/domain metadata filled in.
3. At pilot end (or weekly), aggregate and deliver JSON/HTML to stakeholders.
4. Review section 8 (recommended path) for licensed-SDK next steps.

Trigger options you implement:

- **Manual** — run aggregation after the pilot
- **Scheduled** — your cron job calls `aggregate_shadow_report()`
- **Threshold** — generate when turn count or calendar window is reached
- **Admin UI** — button that exports current turns and renders HTML

---

## CSAM compliance signals

This package does **not** detect CSAM content directly. CSAM-related law
matches surface only when an **upstream classifier** you operate emits the
relevant tag for a turn. Without that wiring, CSAM statutes will not appear in
compliance exposure even if content is present.

---

## Licensed SASKI engine (Phase 2)

You are not required to use the baseline analyzer. Any object satisfying the
`AnalysisResult` protocol works with `result_to_jsonl_turn`, evidence helpers,
and the aggregator. The optional adapter at `saski_shadow.integrations.saski_sdk`
maps licensed engine output onto the same shape — same JSONL pipeline and report
format, no re-architecture.

Contact [info@techviz.us](mailto:info@techviz.us) or
[www.techviz.us](https://www.techviz.us) for licensed SDK evaluation.

---

## Integration checklist

- [ ] `analyze_turn()` called per chat turn (ideally with `assistant_output`)
- [ ] `user_jurisdiction` and `domain`/`domains` set from your product metadata
- [ ] `evaluate_deployment_mode(..., DeploymentMode.SHADOW)` during pilot
- [ ] Turns persisted via `result_to_jsonl_turn()` (full `engine_summary` included)
- [ ] Report aggregation triggered on your schedule (not automatic)
- [ ] Token-savings inputs supplied if section 3 should be populated
- [ ] Stakeholders understand baseline-only limits (see README *What it does not do*)
