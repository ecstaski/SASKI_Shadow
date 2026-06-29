# Syncing the Law Set (`starter.py`)

This is the **saski-shadow side** of the law-data contract. The
`saski-law-registry` repo's `AGENTS.md` documents the same relationship from
the registry side. Read both before resyncing.

---

## Pending Registry Changes

> **For Registry Cursor — not yet applied. Do NOT hand-edit `starter.py` for
> this; it must come through the normal registry → resync flow (sections 2–3
> below).**

**California mental-health domain gap (Gap 5).** California currently has no law
in the `mental_health` domain, so `match_laws("US-CA", "mental_health")` returns
`[]`. Two existing California laws are relevant to mental/behavioral-health
contexts but are tagged `healthcare` only. Decision (C=A): **add duplicate
entries** to `laws.json` rather than reclassifying or adding a per-law domain
list, so the existing `healthcare` coverage is left untouched.

Registry Cursor needs to add the following **two new `laws.json` entries**:

| New `law_id` | Mirrors existing entry | `domain` |
|---|---|---|
| `US-CA-AB3030-HEALTH-MH` | `US-CA-AB3030-HEALTH` | `mental_health` |
| `US-CA-HEALTH-ADVICE-AI-MH` | `US-CA-HEALTH-ADVICE-AI` | `mental_health` |

For each new entry, copy the source entry verbatim and change only:
- `law_id` → the new `-MH`-suffixed id above
- `domain` → `mental_health`

All other fields (`jurisdiction` = `US-CA`, `citation`, `effective_date`,
`date_added`, `note`, and the registry-only UI fields) stay identical to the
source entry. These are duplicate cross-domain listings of the same statutes,
not new statutes.

**Downstream impact once this lands and is resynced here (do these in the same
resync, per section 3 step 7):**
- `STARTER_LAWS` count rises from **74 → 76**; update
  `tests/test_laws.py::test_starter_set_has_expected_count_and_fact_only_fields`.
- README Law Coverage `mental_health` figure changes (currently "7 laws / 6
  states" → "9 laws / 7 states"); `test_readme_law_coverage_counts_match_starter_set`
  enforces this in lockstep.
- `tests/test_laws.py::test_domain_must_match_exactly` currently asserts
  `match_laws("US-CA", "mental_health") == []`; it must be inverted to expect the
  two new `-MH` law ids (see the TODO already placed on that test).
- `test_exact_state_domain_match_names_specific_law` (the CA `healthcare` set)
  stays unchanged under the duplicate-entry approach — verify it still passes.

Remove this section once the resync is complete.

---

## 1. What is being synced

| | Source of truth | Local copy |
|---|---|---|
| Location | `laws.json` in [`saski-law-registry`](https://github.com/ecstaski/saski-law-registry) | `saski_shadow/laws/starter.py` |
| Schema | 12-field JSON objects | 7-field Python `dict` literals in the `STARTER_LAWS` tuple |

`starter.py` is a **manually synced subset** of `laws.json`. There is **no
network call and no automatic propagation** — every change to `laws.json` (new,
corrected, or removed entries) reaches `starter.py` only through a deliberate
manual resync.

---

## 2. When to sync

Resync any time `laws.json` in `saski-law-registry` changes:

- new entries added
- existing entries corrected
- entries removed

Before syncing, check the registry's commit history to confirm exactly what
changed, so the diff you apply to `starter.py` is intentional and minimal.

---

## 3. How to sync (step by step)

1. **Shallow-clone the registry to a temp dir.** Do not assume anonymous
   public access — clone with your normal credentials:

   ```bash
   tmp=$(mktemp -d)
   git clone --depth 1 https://github.com/ecstaski/saski-law-registry "$tmp/reg"
   ```

2. **Read `laws.json`** from `$tmp/reg/laws.json`.

3. **Identify new or changed entries** vs the current `STARTER_LAWS` content
   (compare by `law_id`, then compare the 7 kept fields for existing ids).

4. **Extract the 7 kept fields, in `starter.py` field order**, for each new or
   changed entry. Pull the content programmatically from the cloned
   `laws.json` — never hand-type it:

   ```
   law_id, jurisdiction, domain, citation, effective_date, date_added, note
   ```

5. **Apply the changes to `STARTER_LAWS`** in `saski_shadow/laws/starter.py`:
   - New entries: append as Python `dict` literals matching the existing
     format exactly (4-space indent, double-quoted keys/values, trailing
     commas).
   - Changed entries: update only the affected fields in the existing dict.
   - Removed entries: delete the corresponding dict.

6. **Confirm the total count matches `laws.json`:**

   ```bash
   python3 -c "from saski_shadow.laws import STARTER_LAWS; print(len(STARTER_LAWS))"
   ```

7. **Run the validator / tests** (see below) and confirm they pass. If a count
   or coverage guard fails because the set legitimately grew, that guard and
   the README figures it checks must be updated as part of the same sync —
   flag it for review rather than silently editing around it.

   ```bash
   python3 -m pytest -q
   ```

8. **Clean up the temp clone:**

   ```bash
   rm -rf "$tmp"
   ```

9. **Leave changes unstaged.** Stephen reviews and commits manually.

---

## 4. Field mapping (12 → 7)

`laws.json` carries 12 fields per entry. `starter.py` keeps **7** and drops
**5**.

**Kept (verbatim, content unchanged):**

| `laws.json` field | `starter.py` field |
|---|---|
| `law_id` | `law_id` |
| `jurisdiction` | `jurisdiction` |
| `domain` | `domain` |
| `citation` | `citation` |
| `effective_date` | `effective_date` |
| `date_added` | `date_added` |
| `note` | `note` |

Note the field-order difference: `laws.json` emits
`... citation, effective_date, note, date_added`, while `starter.py` uses
`... effective_date, date_added, note`. Reorder to the `starter.py` convention
— this is ordering only, not a content change.

**Dropped (UI / coverage-layer concerns, not needed for the compliance signal layer):**

| Dropped field | Why it's not in `starter.py` |
|---|---|
| `scope_status` | Registry-side scoping metadata |
| `regulatory_category` | Presentation/grouping label |
| `status` | Presentation/lifecycle label |
| `display_name` | UI display string |
| `sample_prompts` | Demo/illustration data |

The signal layer matches purely on `jurisdiction` (hierarchical) and `domain`
(exact) and reports the public statute facts; the dropped fields play no part
in that.

---

## 5. What not to do

- **Never paste entry content manually into a prompt.** Always pull from the
  live `laws.json` in a fresh clone.
- **Never add SASKI enforcement or coverage language to `starter.py`.** Public
  statute facts only, identical to `laws.json` content. No thresholds, scoring,
  trigger maps, or coverage/enforcement-mapping data.
- **Never commit or push without Stephen's explicit review.**

---

## 6. Relationship to the registry

`saski-law-registry` is the single source of truth. Its `AGENTS.md` documents
this sync relationship from the registry side; this file (`SYNC.md`) is the
saski-shadow side of the same contract. If the two ever disagree, the registry
wins for content and Stephen decides how `starter.py` adapts.
