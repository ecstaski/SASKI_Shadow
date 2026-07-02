# Integrating saski-shadow into your chatbot

This guide is for application developers wiring shadow mode into a
conversational AI product (sandbox or production pilot). It assumes Python 3
on your backend. For package overview, see [README.md](README.md).

Shadow mode **observes** traffic only. It does not block, modify, or suppress
LLM output. Use `DeploymentMode.SHADOW` during a pilot so user-facing behavior
stays unchanged while you collect findings.

---

## Installation

Install into the **same Python environment** as your chatbot backend. The
package is not published to PyPI yet; install from the repository (pin a tag
or commit for reproducible deploys):

```bash
pip install "saski-shadow @ git+https://github.com/mytrustedai/saski-shadow.git@<tag>"
```

Verify the CLI entry point:

```bash
which saski-shadow          # should point inside your venv, not /usr/local/bin
saski-shadow aggregate --help
```

If `saski-shadow` is not on your PATH, use your venv's pip explicitly
(`./venv/bin/pip install ...`) and invoke aggregation via module instead (see
[Generating reports](#generating-reports)).

For local development on a clone of this repo:

```bash
pip install -e .
```

**Zero runtime dependencies** for the core package — only the Python standard
library at runtime.

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
    │                     (off the hot path — see Persistence)
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
    evaluate_deployment_mode,
    result_to_jsonl_turn,
)
from saski_shadow.analyzer import analyze_turn

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

### Env-gated shadow mode (recommended)

Gate shadow observation behind environment variables so you can enable or
disable a pilot without a code deploy:

```text
SHADOW_MODE_ENABLED=true
SHADOW_USER_JURISDICTION=US-CA
SHADOW_DOMAINS=mental_health,consumer_chatbot
SHADOW_TURNS_JSONL=turns.jsonl          # optional path override
```

Read these at startup. Skip all shadow I/O when `SHADOW_MODE_ENABLED` is not
`true`. Map product-specific audience tags to the regulated `mode` argument
(e.g. child-facing → `"child"`, clinical adult → `"patient"`).

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

### Do not block the chat path

Append turns **off the request hot path**. In FastAPI, use `background_tasks`;
in other frameworks, a queue, thread pool, or fire-and-forget write. Shadow
persistence must never delay or fail the user-facing LLM response — wrap
shadow I/O in `try/except` and log failures locally.

### Ephemeral cloud disk

On PaaS hosts (Render, Heroku, etc.), a local JSONL path is often on
**ephemeral disk** — turns survive restarts but may be lost on redeploy or
scale-to-zero. For a short sandbox pilot that is usually fine; copy the file
before redeploying, or point `SHADOW_TURNS_JSONL` at durable storage (S3,
mounted volume, database export) for longer pilots.

### Pulling turns from a remote host

For a manual pilot, copy the JSONL from your server before aggregating locally:

```bash
scp user@host:/path/to/shadow_turns.jsonl ./pilot_turns.jsonl
```

Then run aggregation against the local copy (see below).

---

## Generating reports

Aggregation is a **two-step** deliverable: JSON first, then HTML.

### 1. JSON report (CLI)

From a directory where your input paths resolve (repo root or any working dir):

```bash
saski-shadow aggregate \
  --input pilot_turns.jsonl \
  --output report/report.json \
  --config pricing.json \
  --schema v1
```

Copy [`pricing.example.json`](pricing.example.json) to `pricing.json` locally
and fill in your token counts. `pricing.json` should not be committed (it is
gitignored in this repo's dev layout).

**Alternative** if the `saski-shadow` script is not installed — run from the
package root or any environment where `saski_shadow` is importable:

```bash
python3 -m saski_shadow.aggregate.report aggregate \
  --input pilot_turns.jsonl \
  --output report/report.json \
  --config pricing.json
```

A harmless `RuntimeWarning` about `sys.modules` may appear; the command still
succeeds. Prefer `saski-shadow aggregate` when the entry point is installed.

Pass `--config pricing.json` to populate the token-savings section (see
[Token savings](#token-savings-how-the-estimate-works)). Without it, section 3
reports `basis: insufficient_inputs`.

### 2. HTML report (programmatic)

The CLI writes JSON only. Render customer-facing HTML in a second step:

```bash
python3 -c "
import json
from saski_shadow.reporting import generate_html_report
report = json.load(open('report/report.json', encoding='utf-8'))
generate_html_report(report, 'report/report.html')
"
```

Or aggregate and render in one script:

```python
from saski_shadow import aggregate_shadow_report, load_turns_jsonl
from saski_shadow.reporting import generate_html_report

turns = load_turns_jsonl("pilot_turns.jsonl")
report = aggregate_shadow_report(
    turns,
    prospect_inputs={
        "legacy_system_prompt_tokens": 450,
        "lean_product_prompt_tokens": 103,
    },
)
generate_html_report(report, "report/report.html")
```

Filter by date range or session before aggregating by slicing the turn list or
using `period_start_utc` / `period_end_utc` on `aggregate_shadow_report()`.

### End-to-end example

```bash
# After pilot — from your machine or CI
saski-shadow aggregate \
  --input outputs/pilot/shadow_turns.jsonl \
  --output outputs/pilot/report/report.json \
  --config pricing.json

python3 -c "
import json
from saski_shadow.reporting import generate_html_report
p = 'outputs/pilot/report'
report = json.load(open(f'{p}/report.json', encoding='utf-8'))
generate_html_report(report, f'{p}/report.html')
"

open outputs/pilot/report/report.html   # macOS; use xdg-open on Linux
```

---

## Token savings (how the estimate works)

The token-savings section is an **estimate**, not a measurement. It contains
**no proprietary SASKI constants** — every number is computed by visible
arithmetic from inputs *you* supply, applied to the turn counts observed in
your pilot. Each output field stays `null` until the inputs it depends on are
provided, and the section always reports its `basis`
(`estimated_from_integrator_inputs` or `insufficient_inputs`).

### `pricing.json` shape

Token fields must be under **`prospect_inputs`** when using `--config`:

```json
{
  "prospect_inputs": {
    "legacy_system_prompt_tokens": 450,
    "lean_product_prompt_tokens": 103,
    "regulated_mode_floor_tokens": 85,
    "warning_append_tokens": 50
  }
}
```

The CLI also accepts the same four keys at the **top level** of the config file
(legacy flat layout); they are hoisted into `prospect_inputs` automatically.
[`pricing.example.json`](pricing.example.json) uses the wrapped form above.

Pass the same dict to `aggregate_shadow_report(prospect_inputs={...})` when
aggregating programmatically.

### Measuring your inputs

- **`legacy_system_prompt_tokens` (L)** — token cost of your current ungoverned
  system prompt per LLM turn. Measure with your model's tokenizer, or estimate
  as `len(prompt_chars) / 4` for a first pass.
- **`lean_product_prompt_tokens` (P)** — your estimate for the governed lean
  product prompt per turn (not measured by this package).

Per-turn arithmetic (keyed on governance tier and regulated `mode`):

```text
floor   = regulated_mode_floor_tokens if mode is regulated else 0
Tier 1  saved = max(0, L - (P + floor))
Tier 2  saved = max(0, L - (P + floor + warning_append))
Tier 3  saved = L            # enforce mode would not call the LLM at all
tokens_saved  = sum of per-turn saved across observed turns
```

Optional overrides: `regulated_mode_floor_tokens` (default **85**),
`warning_append_tokens` (default **50**). Omit either required input (`L` or
`P`) and all savings fields return `null` with `basis = "insufficient_inputs"`.

**No dollar figure is ever computed.** Multiply `tokens_saved` by your own
input cost per token:
`dollar_savings = tokens_saved × (your cost per token)`.

---

## Pilot workflow

A typical **7-day shadow pilot** (recommended duration, not enforced):

1. Deploy shadow mode on real or sandbox traffic.
2. Persist every turn with jurisdiction/domain metadata filled in.
3. Copy or export the turn store before redeploying (if using ephemeral disk).
4. At pilot end (or weekly), aggregate JSON + HTML and deliver to stakeholders.
5. Review section 8 (recommended path) for licensed-SDK next steps.

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

Contact [support@saski.io](mailto:support@saski.io) or
[www.saski.io](https://www.saski.io) for licensed SDK evaluation.

---

## Integration checklist

- [ ] Package installed in the same venv as the chatbot (`saski-shadow` or `pip install -e .`)
- [ ] Shadow mode env-gated (`SHADOW_MODE_ENABLED`, jurisdiction, domains)
- [ ] `analyze_turn()` called per chat turn (ideally with `assistant_output`)
- [ ] `user_jurisdiction` and `domain`/`domains` set from your product metadata
- [ ] `evaluate_deployment_mode(..., DeploymentMode.SHADOW)` during pilot
- [ ] Turns persisted via `result_to_jsonl_turn()` off the hot path (background task)
- [ ] Turn store copied or durable before redeploy (if on ephemeral cloud disk)
- [ ] Report aggregation triggered on your schedule (not automatic)
- [ ] `pricing.json` with `prospect_inputs` (or programmatic equivalent) if section 3 should populate
- [ ] HTML generated via `generate_html_report()` after JSON aggregation
- [ ] Stakeholders understand baseline-only limits (see README *What it does not do*)
