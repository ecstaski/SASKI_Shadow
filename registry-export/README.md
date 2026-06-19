# saski-law-registry

The single source of truth for **public AI law facts** used across SASKI
projects. This repository holds plain, public-domain reference data only — it
contains no enforcement logic.

## What this is

A small, curated dataset of public US AI law facts (`laws.json`). Each entry
records only:

| Field | Meaning |
| --- | --- |
| `law_id` | Opaque, stable identifier for the entry. |
| `jurisdiction` | Hierarchical jurisdiction code (e.g. `US-CA`, `US-NY-NYC`). |
| `domain` | The conversational-AI signal area the law relates to. |
| `citation` | The public statute / bill / rule citation. |
| `effective_date` | When the law takes (or took) effect (`YYYY-MM-DD`). |
| `note` | A plain-language, non-authoritative summary. |
| `date_added` | When the entry was added to this registry (`YYYY-MM-DD`). |

## Who consumes it

This registry is the upstream source for several downstream consumers:

- **`saski-shadow`** — the free, open-source baseline detector reads these
  facts to name laws by jurisdiction and domain.
- **The public website compliance matrix** — renders these facts directly.
- **The licensed SASKI engine** — incorporates these facts via a **private,
  build-time join**, not a runtime dependency. The engine never calls this
  repository at runtime, and this repository never contains any engine logic.

Keeping the facts here, separate from any consumer, means a citation or
effective date is corrected in exactly one place.

## What this explicitly is NOT

- **No enforcement logic.** No mappings from a law to an action, no routing,
  no blocking rules.
- **No thresholds, scores, or weights.** Nothing tunable or numeric beyond the
  public dates above.
- **No internal taxonomy.** The `domain` values are coarse, public-facing
  signal areas only — not any proprietary classification system.
- **No raw text, user data, or model behavior.**

If a field that isn't in the table above ever appears in `laws.json`, treat it
as a defect and remove it — this dataset is intentionally facts-only.

## Scope

Current scope is **US state and federal laws relevant to conversational AI
safety**. It is:

- **Not exhaustive** of all AI law, even within the US.
- **Not yet international** — no EU, UK, or other non-US jurisdictions.

Coverage grows over time. New entries should carry their own real `date_added`
rather than reusing an earlier backfill date.

## Not legal advice

This dataset is **informational only and is not legal advice**. The
plain-language `note` fields are summaries for orientation, not authoritative
statements of the law. Always consult the cited primary source and qualified
counsel for compliance decisions.

## License

**TBD — pending legal review.** A license has not yet been decided. Until a
license is added here, no usage rights are granted by default; do not assume
this data is freely reusable until this section is updated.
