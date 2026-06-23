# Shadow Follow-up Items — June 23 2026

## Public launch blockers

Shadow mode public launch has not yet been 
assessed. The following items should be reviewed 
before launch:

1. README accuracy — coverage figures are current
   (73 laws / 36 jurisdictions as of June 23, 2026)
   but the disclaimer language in sections 2, 3, 
   and 5 should be reviewed to ensure it accurately 
   reflects the current baseline-only positioning.

2. Upgrade messaging — starter.py and README both
   reference upgrading to the licensed engine. 
   Verify this messaging is current and points to 
   the correct contact/URL (info@techviz.us, 
   www.techviz.us).

3. CSAM classifier dependency disclosure — shadow 
   mode detects CSAM-related content via an upstream 
   tag-gated classifier. If that upstream classifier 
   does not fire, shadow mode will not surface CSAM 
   compliance signals. This limitation should be 
   explicitly disclosed in the README or documentation 
   before public launch.

4. Federal law matching — the 13 federal entries
   (8 Tier 1 + 5 Tier 2) match any US-prefixed 
   turn via the prefix-based matcher. This is 
   correct behavior but should be documented so 
   integrators understand that a US-CA turn will 
   surface both state and federal law matches.

5. test_federal_law_matches_any_us_subjurisdiction
   covers Tier 1 federal matching at the unit level
   but no dedicated integration test asserts that
   Tier 2 federal entries (US-FTC-HBNR, 
   US-42-CFR-PART-2, US-ADEA, US-FCRA, US-ACA-1557) 
   appear in generated reports. Consider adding a 
   test for this before public launch.

## Sync discipline

SYNC.md documents the manual resync process.
After any laws.json update in saski-law-registry,
Shadow Cursor must run a resync pass before the
next public-facing release. The last resync was
June 23, 2026 (73 entries).

## IP boundary reminders

- starter.py must never contain SASKI enforcement
  logic, thresholds, scoring, or internal module 
  names
- Registry-side coverage/enforcement-mapping data
  lives in saski-law-registry only — never reproduce 
  or reference it in this repo
- The SDK's internal composer/intent-tag vocabulary
  must not appear verbatim in any public file in this 
  repo
