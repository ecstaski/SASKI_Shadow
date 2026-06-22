# Syncing the Law Set (`starter.py`)

This is the **saski-shadow side** of the law-data contract. The
`saski-law-registry` repo's `AGENTS.md` documents the same relationship from
the registry side. Read both before resyncing.

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
