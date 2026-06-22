# saski-shadow — Agent Rules & Guidelines

**Read this before making any changes.**

---

## What this repo is

`saski-shadow` is a public, open-source, zero-runtime-dependency baseline AI safety/compliance detection package. It is NOT clinical-grade — the README explicitly discloses it as baseline-only, less accurate than the licensed SASKI SDK, intended as a local, self-contained shadow-pilot tool.

**When uncertain about scope or IP exposure: ASK THE USER first.**

---

## Mandatory Pre-Change Checklist

Before editing any existing file:
1. Create a timestamped backup: `cp target_file.ext target_file.ext.bak.$(date +%Y%m%d_%H%M%S)`
2. Verify the backup exists before proceeding
3. Identify whether the change touches the IP boundary (see below)

**Skip backups for pure read-only research tasks** — only required when actually modifying a file.

---

## IP Boundary Rules (NEVER violate)

This repo must contain zero proprietary logic from the private `sasi-sdk` engine:
- Never import or reference `sasi_sdk` internals
- Never reuse the internal 76-tag composer vocabulary or any internal trigger-tag strings verbatim
- Never include statute-specific enforcement logic, thresholds, scoring, or internal module names
- Never add a runtime dependency — this package promises zero deps, full stop
- Never include `saski_coverage_status`, `missing_saski_capability`, or any private coverage/enforcement-mapping data — that lives exclusively in the private engine

If a request would cross this boundary, flag it and ask before proceeding.

---

## Repo Structure

```
saski_shadow/
├── enums.py / hashing.py / types.py / deployment.py / evidence.py
├── analyzer/         # analyze_turn entry point
├── detectors/        # pii.py, distress.py, policy.py, output_review.py
├── aggregate/        # report.py (8-section report generation)
├── laws/             # starter.py — internal copy, synced FROM saski-law-registry
├── integrations/     # saski_sdk.py (optional licensed-engine adapter)
├── schemas/
tests/
README.md
```

---

## Law Data Sync

`laws/starter.py` is a manually synced internal copy of `saski-law-registry`'s `laws.json` (https://github.com/ecstaski/saski-law-registry) — the public source of truth as of June 2026. It is NOT a live runtime dependency — no network calls. When the registry updates, this file needs a manual or build-step resync; it does not happen automatically.

---

## 🔗 sasi-sdk Relationship & Alignment

The SASKI SDK (private) is the enforcement source of truth
for saski-shadow. This repo consumes the SDK's public
surface and must stay aligned with it. Any Cursor session
in this repo must be aware of this relationship before
making changes to laws, tests, or report schema
documentation.

### What this repo depends on

- `laws.json` in saski-law-registry — source of truth for
  all law entries. `saski_shadow/laws/starter.py` is a
  7-field manually synced subset. Sync process is
  documented in `SYNC.md` in this repo. Never edit
  starter.py entries directly — always resync from the
  registry.
- SDK enforcement machinery — the internal enforcement
  engine in sasi-sdk drives what shadow mode can observe
  and report. Shadow mode can only surface compliance
  signals for laws that the SDK has corresponding
  enforcement paths for. The mapping between registry
  entries and SDK enforcement paths is maintained in
  the private sasi-sdk repo.
- Intent tag vocabulary — tags referenced in shadow
  documentation must match the canonical runtime tag
  list maintained in sasi-sdk. Do not add or reference
  tags in public documentation that do not exist in the
  SDK's runtime allowlist.

### Coverage alignment

A full internal alignment investigation was completed in
June 2026 mapping all 68 registry entries against SDK
enforcement machinery. Results and gap analysis are
documented in the private sasi-sdk repo (AGENTS.md,
section: saski-shadow Relationship & Alignment). Shadow
Cursor sessions should request that document from Stephen
when SDK alignment decisions need to be made.

### Rules for this repo when SDK alignment is in scope

- Before adding a test that asserts a specific compliance
  signal fires for a given law: verify with Stephen that
  the SDK has an enforcement path for that law. Testing
  for signals the SDK cannot produce will produce false
  test failures.
- When SASKI Cursor completes jurisdiction wiring work
  for additional states or federal entries, Shadow Cursor
  will need a follow-up prompt to update test assertions
  and coverage counts. Stephen will coordinate the
  sequencing.
- SYNC.md documents the registry resync process. Follow
  it exactly when laws.json is updated.
- Never reference internal SDK module names, class names,
  tag names, enforcement thresholds, or implementation
  details in any file in this repo.

---

## Testing Requirements

Run the full test suite and confirm lint is clean before any commit. (Confirm exact lint command/tool if unclear — don't assume.)

---

## Git Identity & Push Configuration

- `user.name`: `ecstaski`
- `user.email`: `vwxtski@gmail.com` — set as a repo-local override (`git config --local`), confirmed working as of commit `68443fb`.
- Push auth: HTTPS via the macOS `osxkeychain` credential helper.

---

## Commit Standards

```
TYPE: Brief description (50 chars max)

Longer explanation if needed.
```

Types: `FEAT:` `FIX:` `DOCS:` `TEST:` `CHORE:`

**Stephen approves every commit and push explicitly before it happens. Never commit or push unless instructed.**

---

## Cursor Prompt Conventions

- Every implementation prompt ends by asking whether you agree with the plan or have questions — never execute blind.
- If a prompt references an external AI opinion or design decision not pasted into the conversation, ask for it before proceeding.
- Research-only prompts don't require backups; implementation prompts do.

---

## Prohibited Actions

**NEVER:**
- Expose private SASKI engine logic, thresholds, or vocabulary
- Add a runtime dependency
- Claim statute-specific enforcement the package doesn't actually perform
- Guess when metadata is insufficient — state plainly that it's insufficient instead

---

## Escalation Protocol

| Scenario | Action |
|---|---|
| Request risks IP boundary | STOP, ask before proceeding |
| Unclear scope | ASK USER |
| Conflicting instructions | STOP, flag the conflict |
| Possible security issue | ALERT USER immediately |

---

*Last updated: 2026-06-22*
