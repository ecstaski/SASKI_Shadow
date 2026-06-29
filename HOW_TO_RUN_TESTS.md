# How to Run Sessions and Tests

A plain-English guide to running `saski-shadow` sessions and tests, and reading
the results. No coding required — every command below is something you type into
a terminal and run from the project folder.

**Before you start:** open a terminal and move into the project folder:

```bash
cd /Users/ecstaski/SASKI_SHADOW
```

All commands in this guide assume you are in that folder. This guide uses
`python3`

---

## Section 1 — Running a custom session

The main tool is `scripts/run_session.py`. It takes a list of user messages,
runs each one through the shadow pipeline, optionally sends the (redacted)
message to a real AI model, and writes out files you can read afterward.

### Run the default session, no AI model

This runs the built-in "canonical" 10-turn session and does **not** call any
outside AI. It is the fastest way to see the pipeline work end to end.

```bash
python3 scripts/run_session.py --provider none
```

`--provider none` means "do everything except actually call an AI model." You
still get the full compliance report — you just don't get AI replies.

### Run with Anthropic (Claude)

```bash
python3 scripts/run_session.py --provider anthropic
```

This sends each redacted message to Anthropic's Claude and records the reply.
It requires:

- An `ANTHROPIC_API_KEY` in your `.env` file (see note below).
- The `anthropic` Python package installed (`python3 -m pip install anthropic`).

**Important — model name:** the script's built-in default Claude model name is
out of date and may be rejected by Anthropic. If you get a "model not found"
error, tell it which model to use for that run:

```bash
SASKI_ANTHROPIC_MODEL=claude-sonnet-4-6 python3 scripts/run_session.py --provider anthropic
```

(You can list the models available on your account, or ask your developer for
the current recommended one.)

### Run with OpenAI (GPT)

```bash
python3 scripts/run_session.py --provider openai
```

This requires an `OPENAI_API_KEY` in your `.env` file and the `openai` package
installed (`python3 -m pip install openai`). To pick a specific model for a run:

```bash
SASKI_OPENAI_MODEL=gpt-4o-mini python3 scripts/run_session.py --provider openai
```

### Change where the output goes

By default, output is written under `outputs/`. To send it somewhere else for a
single run, add `--outdir`:

```bash
python3 scripts/run_session.py --provider none --outdir my_results
```

You can also set a permanent default by copying `saski_shadow_config.example.json`
to `saski_shadow_config.json` and editing the `output_dir` value. The `--outdir`
flag always wins over the config file, and the config file wins over the
built-in default. When the run starts it prints which output directory it is
using and where that setting came from.

### Where the output files land

Every run creates a new timestamped folder, for example:

```
outputs/20260624T230815Z/
```

Inside that folder you get three files:

| File | What it is |
|---|---|
| `session.log` | Human-readable, turn-by-turn log. **Start here.** |
| `report.json` | The full customer-facing compliance report. |
| `turns.jsonl` | Raw pipeline data the report is built from (you rarely need this). |

Section 5 explains how to read each one.

---

## Section 2 — Running a focused session (example: all patient mode, all US-CA)

Sometimes you want to test one specific scenario — for example: *"5 turns, all in
patient mode, all in California (US-CA), all in the healthcare domain."* You do
this by writing your own **session file** and pointing the runner at it.

### Step 1 — Create the session file (JSON)

A custom session file is a plain **JSON** file: a list of turns, where each turn
has a `message` and a `session_context`. Save the following as
`my_session.json` in the project folder.

> **Note on file format:** custom session files passed with `--session` must be
> **JSON** files (ending in `.json`). The built-in canonical session that runs by
> default is written as a Python file for developers — that is an internal
> developer fixture and a different thing. For your own custom sessions, always
> use a `.json` file like the one below.

```json
[
  {
    "message": "My doctor told me I need surgery and I am scared.",
    "session_context": {
      "mode": "patient",
      "user_jurisdiction": "US-CA",
      "domain": "healthcare",
      "enforcement_mode": "shadow"
    }
  },
  {
    "message": "Can you explain what my insurance has to cover under California law?",
    "session_context": {
      "mode": "patient",
      "user_jurisdiction": "US-CA",
      "domain": "healthcare",
      "enforcement_mode": "shadow"
    }
  },
  {
    "message": "My SSN is 123-45-6789 and my insurance ID is BCBS-99001.",
    "session_context": {
      "mode": "patient",
      "user_jurisdiction": "US-CA",
      "domain": "healthcare",
      "enforcement_mode": "shadow"
    }
  },
  {
    "message": "I feel really hopeless about my diagnosis.",
    "session_context": {
      "mode": "patient",
      "user_jurisdiction": "US-CA",
      "domain": "healthcare",
      "enforcement_mode": "shadow"
    },
    "extra_distress_indicators": ["feel hopeless", "scared"]
  },
  {
    "message": "What are my rights if my doctor shares my records without permission?",
    "session_context": {
      "mode": "patient",
      "user_jurisdiction": "US-CA",
      "domain": "healthcare",
      "enforcement_mode": "shadow"
    }
  }
]
```

A few things to notice:

- The whole file is wrapped in square brackets `[ ... ]` — that is the list of
  turns. Each turn is wrapped in curly braces `{ ... }`.
- Every text value uses **double quotes** `"like this"` (this is a JSON rule).
- `extra_distress_indicators` (on the 4th turn) sits **next to**
  `session_context`, not inside it. It is optional — see Section 3.
- Put a comma between turns, but **not** after the last one.

### Step 2 — Run it

```bash
python3 scripts/run_session.py --session my_session.json --provider none
```

Swap `--provider none` for `--provider anthropic` or `--provider openai` if you
want real AI replies in the log. The output lands in the usual `outputs/`
folder (see Section 1).

---

## Section 3 — Available modes, jurisdictions, and domains

These are the values you can mix and match inside `session_context`.

### Modes (12)

The mode is a label describing who the AI is talking to or acting as. In the
shadow package it is recorded for reporting only.

| Mode | Plain English |
|---|---|
| `child` | For kids' apps (e.g. Roblox, children's chatbots). |
| `student` | For education and tutoring contexts. |
| `patient` | For someone receiving healthcare or medical guidance. |
| `therapist` | For a licensed-therapy-style assistant. |
| `mental_health_support` | For general mental-health support (non-clinical). |
| `wellness_coaching` | For general wellness and lifestyle coaching. |
| `career_coaching` | For career and job-search coaching. |
| `sports_coaching` | For athletic and fitness coaching. |
| `business` | For business and workplace use. |
| `general_assistant` | For an everyday general-purpose assistant. |
| `hr_recruiting` | For hiring, recruiting, and applicant screening. |
| `default` | A neutral fallback when nothing more specific fits. |

### Domains (5)

The domain tells the system which area of law to check against.

| Domain | Plain English |
|---|---|
| `consumer_chatbot` | General consumer-facing chatbots and assistants. |
| `mental_health` | Mental-health and emotional-support contexts. |
| `healthcare` | Medical, clinical, and health-record contexts. |
| `employment` | Hiring, workplace, and employment decisions. |
| `csam` | Child-safety / child sexual abuse material protections. |

### Jurisdictions

A jurisdiction is a place whose laws apply. You write it as a code:

- `US` on its own means **federal laws only** (no specific state).
- `US-CA`, `US-NY`, `US-TX`, etc. mean a **specific state** (California, New
  York, Texas). State codes also include the relevant federal laws.
- `US-NY-NYC` means a **specific city** (New York City) and includes that city's
  rules plus the state and federal ones above it.

So jurisdictions stack: city → state → federal. Pick the most specific one that
matches your scenario.

### Using more than one domain on a single turn

If one message touches two areas at once, use `domains` (plural, a list) instead
of `domain` (singular). For example, a child being asked for photos online
touches both consumer-chatbot rules and child-safety rules:

```json
"session_context": {
  "mode": "child",
  "user_jurisdiction": "US",
  "domains": ["consumer_chatbot", "csam"],
  "enforcement_mode": "shadow"
}
```

The report will then surface laws from **both** domains for that turn.

### What `extra_distress_indicators` does

The baseline package ships a small built-in list of common, direct crisis
phrases (e.g. "want to die", "kill myself", "suicidal") and will flag those on
its own. This is **common phrase awareness only — not clinical crisis
detection**: it catches literal phrasings but misses indirect, contextual, or
semantic distress. `extra_distress_indicators` is an optional list of additional
phrases that, if found in the message, also get counted as an escalation signal:

```json
"extra_distress_indicators": ["feel hopeless", "scared"]
```

Use it when you want to add scenario-specific phrases on top of the built-in
list. Leave it out for normal turns. (Clinical-grade crisis detection that does
not depend on a phrase list — and that catches indirect and contextual signals —
is a feature of the licensed SASKI engine, not this baseline package.)

---

## Section 4 — Running the test suite

Tests confirm the package still behaves correctly. Run them from the project
folder.

### Run everything

```bash
pytest
```

You should see a line like `155 passed, 2 skipped`. "Passed" is good. The 2
"skipped" are expected — see below.

### Run one group of tests

The tests are organized into four "axes," each a focused area:

```bash
pytest tests/harness/axis1_matching.py     # law matching (right laws for the jurisdiction/domain)
pytest tests/harness/axis2_detection.py    # detection (PII, distress signals)
pytest tests/harness/axis3_pipeline.py     # full pipeline (end-to-end behavior)
pytest tests/harness/axis4_live.py         # live AI-model tests (off by default)
```

### Run the live AI tests

The live tests actually call an AI provider, so they are turned off unless you
opt in. They require API keys **and** a flag:

```bash
SASKI_RUN_LIVE_TESTS=1 pytest tests/harness/axis4_live.py
```

### Run a single test by name

If you know part of a test's name, use `-k`:

```bash
pytest -k "multi_domain"
```

This runs only tests whose names contain `multi_domain`.

### About the 2 skipped tests

When you run `pytest`, two tests are skipped. **This is normal and not a
problem.** They are the live AI-model tests, which stay off until you set
`SASKI_RUN_LIVE_TESTS=1` and provide API keys. Skipped simply means "not run
this time," not "failed."

### What to do if a test fails

- Read the failure output carefully — it usually names the test and shows what
  it expected versus what it got.
- **Do not edit the test files to make them pass** unless you understand exactly
  why the test is failing. A failing test is often telling you something real
  changed. When in doubt, share the output with your developer before changing
  anything.

---

## Section 5 — Reading the output files

Each run writes three files into its `outputs/<timestamp>/` folder.

### `session.log` — the human-readable log

This is the easiest file to read. For each turn it shows a block like this:

```
--- turn 0 ---
mode:          child
jurisdiction:  US-CA
domain(s):     consumer_chatbot
outcome:       allow
risk_band:     low
pii_detected:  False
pii_types:     []
escalation:    False
redacted_msg:  How do I stay safe when chatting with strangers in an app?
llm_reply:     (the AI's response, if you ran with a provider)
```

What each field means:

| Field | Plain English |
|---|---|
| `mode` | The mode you set for this turn. |
| `jurisdiction` | The place whose laws were checked. |
| `domain(s)` | The area(s) of law checked. |
| `outcome` | The baseline result for the turn (e.g. `allow`). |
| `risk_band` | A simple risk label (e.g. `low`). |
| `pii_detected` | `True` if personal info (like an SSN or email) was found. |
| `pii_types` | Which kinds of personal info were found. |
| `escalation` | `True` if a distress indicator was matched. |
| `redacted_msg` | The cleaned-up message (personal info removed) that would be sent to the AI. |
| `llm_reply` | The AI model's actual reply (only present if you used a provider). |

### `report.json` — the customer-facing report

This is the structured report a prospect would see. It has 8 main sections:

| Section | In one sentence |
|---|---|
| `pii_phi_detection_summary` | How much personal/health info was detected. |
| `compliance_exposure_examples` | Which laws matched the session's jurisdictions and domains. |
| `token_savings_calculation` | Estimated **tokens** saved (only when you supply the two pricing inputs). Reports tokens only — never a dollar figure. |
| `envelope_evidence_sample` | A sample of the tamper-evidence record kept per turn. |
| `escalation_signal_count` | How many distress/escalation signals were seen. |
| `unsafe_flow_documentation` | Any unsafe-content flows observed. |
| `latency_impact_report` | How much time the pipeline added. |
| `recommended_path` | The suggested next step toward full compliance. |

There is also a 9th section, **`sdk_integration_signals`**, described next.

### `turns.jsonl` — the raw data

This is the raw, machine-readable record of every turn (one line per turn). It
is what the report is built from. You will rarely need to open this directly —
`session.log` and `report.json` cover the human-readable view.

### The SDK Integration Signals section (in the log and the report)

At the bottom of `session.log` (and inside `report.json`) is an **SDK
INTEGRATION SIGNALS** section. These are plain-English flags telling you what the
licensed SASKI SDK would do differently on this traffic. Each has a severity:
`info` (just so you know), `warning` (worth attention), or `action_required`
(should be addressed before production).

| Signal | What it means / suggested action |
|---|---|
| **SIS-001** | Distress was detected using a small built-in list of common crisis phrases plus any you supplied; the licensed engine provides clinical-grade detection without phrase lists and catches indirect/contextual signals. |
| **SIS-002** | Laws were found that aren't in force yet but will be — plan for their effective dates. |
| **SIS-003** | Some turns used multiple domains at once; double-check your domain settings per turn. |
| **SIS-004** | Personal info was detected; the licensed engine offers stronger, jurisdiction-aware redaction. |
| **SIS-005** | The session spanned multiple domains but cross-domain isolation wasn't explicitly tested — run negative tests before production. |
| **SIS-006** | No crisis-level signals occurred, so crisis handling wasn't exercised; verify crisis paths with the licensed engine. |

A signal only appears when its condition is actually met. If nothing applies, the
log simply says *"No integration signals detected for this session."*

For any of these, the contact for the licensed SDK is **info@techviz.us**.

---

## Section 6 — Quick reference card

Day-to-day commands (run from the project folder):

| I want to… | Command |
|---|---|
| Run the default session, no AI | `python3 scripts/run_session.py --provider none` |
| Run with Claude | `python3 scripts/run_session.py --provider anthropic` |
| Run with OpenAI | `python3 scripts/run_session.py --provider openai` |
| Run my own session file | `python3 scripts/run_session.py --session my_session.json --provider none` |
| Send output somewhere else | `python3 scripts/run_session.py --provider none --outdir my_results` |
| Pick a Claude model for a run | `SASKI_ANTHROPIC_MODEL=claude-sonnet-4-6 python3 scripts/run_session.py --provider anthropic` |
| Run all tests | `pytest` |
| Run one test group | `pytest tests/harness/axis1_matching.py` |
| Run live AI tests | `SASKI_RUN_LIVE_TESTS=1 pytest tests/harness/axis4_live.py` |
| Run one test by name | `pytest -k "multi_domain"` |
| Find my latest results | Look in the newest folder under `outputs/`. |

**Reading results:** open `session.log` first (human-readable), then
`report.json` for the full report. The valid building blocks are in Section 3:
12 modes, 5 domains, and jurisdiction codes like `US`, `US-CA`, `US-NY-NYC`.

---

## Section 7 — Generating a report from your own app traffic

`scripts/run_session.py` (Sections 1–2) is for testing with a fixed set of turns
*before* you deploy. Once your app is live and running shadow mode against real
users, you'll want a report built from that **real traffic** instead. That's what
`scripts/generate_report.py` is for.

### What it's for

In a production shadow deployment, your app calls `analyze_turn()` itself on each
user message. You don't run sessions through the test runner — your live app is
the source of turns. `generate_report.py` takes the turns your app has already
saved and produces the same compliance report and findings, on demand, over
whatever slice of traffic you choose.

### How your app should be saving turns

Your app should, for each turn it processes:

1. Call `analyze_turn(...)` to get a result.
2. Convert that result with `result_to_jsonl_turn(...)`.
3. Append the converted turn as **one line** to a JSONL file (a text file where
   each line is one turn in JSON).

Over time this file grows into a complete record of your shadow traffic. That
file is the `--input` to `generate_report.py`. (Your developer wires this up
once; you just point the report tool at the resulting file.)

### Commands

Generate a report from a JSONL file:

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl
```

Send the output somewhere specific (otherwise it goes under `outputs/`, the same
as the session runner, and also respects `saski_shadow_config.json`):

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --outdir path/to/output
```

Only include turns within a date range (dates are `YYYY-MM-DD`, inclusive). You
can give both, or just one:

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --from 2026-06-01 --to 2026-06-30
```

- `--from` alone: everything from that date forward.
- `--to` alone: everything up to and including that date.

Only include the most recent N turns (applied after any date filter):

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --last-n 500
```

Only include turns from one conversation/session:

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --session-id <session_id>
```

Get the report as a polished, self-contained HTML page instead of JSON (writes
`report.html` instead of `report.json`):

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --format html
```

Fill in the token-savings section by handing the tool your two pricing numbers.
Copy `pricing.example.json` to `pricing.json`, edit the values, then:

```bash
python3 scripts/generate_report.py --input path/to/turns.jsonl --pricing pricing.json
```

`pricing.json` needs just two numbers — `legacy_system_prompt_tokens` (your
current ungoverned system-prompt size) and `lean_product_prompt_tokens` (the
governed size). The report shows **tokens saved only**; it never prints a dollar
amount. `pricing.json` is gitignored so your figures stay local. Both
`--format html` and `--pricing` also work on `run_session.py`.

You can combine these flags. If a line in the file is corrupted it is skipped
with a warning (the run does not crash), and if no turns are left after filtering
the tool tells you and writes nothing.

### What you get

Output lands in `outputs/report_<timestamp>/` (or your `--outdir`) with three
files:

| File | What it is |
|---|---|
| `summary.txt` | A plain-English overview — PII, laws matched, escalation, SDK signals, and a recommended next step. **Start here.** |
| `report.json` (or `report.html` with `--format html`) | The full customer-facing compliance report plus SDK integration signals. |
| `internal_findings.log` | Internal-only findings. Note: the per-turn *LLM response quality* flags are **not** available here, because raw AI replies aren't stored in the JSONL — those only appear when you use `run_session.py`. All other internal sections work normally. |

### Which tool do I use?

- **`run_session.py`** — for testing with a fixed set of turns *before* deployment.
- **`generate_report.py`** — for generating reports from real traffic *after* deployment.
