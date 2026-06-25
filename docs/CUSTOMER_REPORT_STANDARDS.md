# Customer Report Standards

Authoritative reference for any customer-facing shadow report (HTML or JSON)
produced by `saski-shadow`. The HTML renderer in
`saski_shadow/reporting/html_report.py` implements these rules; the JSON report
in `saski_shadow/aggregate/report.py` is the data source. If you change a report,
update this file in the same change.

---

## 1. Observation-only language (non-negotiable)

Shadow mode **observes**; it never enforces. Every customer-facing string must
describe what was *observed*, not what was *done*. No report may claim that
`saski-shadow` blocked, modified, redacted, suppressed, or prevented anything.

Every HTML report carries this banner verbatim near the top:

> Observation-only report. In shadow mode SASKI observed this traffic; it did
> not block, modify, or suppress any LLM output. Absence of a finding is not
> evidence of compliance.

**Allowed phrasing:** "observed", "detected", "would have", "in enforce mode the
SDK would", "surfaced for awareness", "counts reflect ... signals only".

**Forbidden phrasing:** "we blocked", "we redacted", "we prevented", "enforced",
"guaranteed", "compliant", "clinical", or any wording implying the baseline
package took an action or made a legal/clinical determination.

---

## 2. Color palette

Defined once as CSS variables in `html_report.py`. Do not introduce ad-hoc colors.

| Token | Hex | Use |
|---|---|---|
| `--navy` | `#1f2a44` | Headings, cover gradient, key numbers |
| `--teal` | `#2f6f6b` | Accent, info-severity signals |
| `--bg` | `#f5f7fa` | Page background, stat tiles |
| `--card` | `#ffffff` | Section card background |
| `--border` | `#e2e6ec` | Card / table borders |
| `--text` | `#1f2430` | Body text |
| `--muted` | `#5b6472` | Secondary text, disclaimers |
| `--sev-action` | `#b23b3b` | `action_required` signals (muted red) |
| `--sev-warning` | `#b9851f` | `warning` signals + observation banner (amber) |
| `--sev-info` | `#2f6f6b` | `info` signals (teal) |

Typography: system UI font stack only (no external/web fonts), 15px base.
Reports must be fully self-contained — inline CSS only, no external scripts,
fonts, images, or network calls.

---

## 3. Section order

Cover page first, then the nine report sections in this fixed order, then footer:

0. Cover (session ID, generated timestamp, reporting period, law-set version,
   laws evaluated, jurisdictions)
1. PII / PHI Detection Summary
2. Compliance Exposure Examples
3. Token Savings Calculation
4. Envelope Evidence Sample
5. Escalation Signal Count
6. Unsafe Flow Documentation
7. Latency Impact Report
8. Recommended Path
9. SDK Integration Signals

Empty sections render an explicit "none observed" state — never an empty box.

---

## 4. Token savings rules

The token-savings section is an **estimate** from two integrator-supplied inputs
applied to observed governance-tier counts. It embeds no proprietary SASKI
constants beyond two documented, observable defaults.

**Required integrator inputs (`prospect_inputs`):**

- `legacy_system_prompt_tokens` (L) — current ungoverned system-prompt cost per
  LLM turn.
- `lean_product_prompt_tokens` (P) — governed lean product-prompt cost per turn.

**Optional advanced overrides (documented defaults shown):**

- `regulated_mode_floor_tokens` — default **85**. Safety-envelope floor added to
  P on governed turns whose mode is `child`, `patient`, or `therapist`.
- `warning_append_tokens` — default **50**. Tokens appended on a Tier 2 turn.

**Per-turn arithmetic (mode-aware):**

```
floor   = regulated_mode_floor_tokens if the turn's mode is regulated else 0
Tier 1  saved = max(0, L - (P + floor))
Tier 2  saved = max(0, L - (P + floor + warning_append))
Tier 3  saved = L           # enforce mode would not call the LLM at all
tokens_saved  = sum of per-turn saved across observed turns
```

**Hard rules:**

- If either required input is missing, `basis` is `insufficient_inputs` and every
  computed `savings` value is `null`. Never invent inputs.
- Tier 3 (escalation) turns count the **full** legacy cost as avoided, because in
  enforce mode the LLM call would not be made.
- **No dollar figure is ever computed.** The report shows only:
  `Dollar savings = tokens_saved × (your input cost per token)`.
- Savings clamp at 0 for Tier 1/2 (never negative); Tier 3 still credits L.

---

## 5. Contact and branding

Use **"SASKI Institute PBC"** consistently — never "Technical Visionaries" or any
prior name.

- Contact line (HTML footer): `Contact SASKI Institute PBC · info@techviz.us · www.techviz.us`
- Footer line: `© 2026 SASKI Institute PBC · Baseline shadow observation report · Not clinical-grade · info@techviz.us`
- Email: `info@techviz.us` · Web: `www.techviz.us`

---

## 6. What this report is **not**

State these limits plainly; never let a reader mistake baseline observation for
enforcement or clinical assessment.

- **Not clinical-grade.** Escalation counts are baseline distress phrase-list
  matches, not crisis detection.
- **Not enforcement.** Nothing was blocked, redacted, or suppressed. "Would have
  blocked" describes a hypothetical enforce-mode path only.
- **Not a compliance guarantee.** Law matches key on integrator-supplied
  jurisdiction/domain metadata; absence of a finding is not evidence of
  compliance.
- **Not the licensed SASKI SDK.** The baseline package is less accurate than the
  licensed engine. SDK integration signals point to where the licensed SDK is
  recommended.
- **No proprietary logic.** Contains no SASKI enforcement thresholds, scoring,
  internal vocabulary, or module names.
