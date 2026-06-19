"""Starter set of real US AI laws and a jurisdiction/domain matcher.

Facts only: ``law_id``, ``jurisdiction``, ``domain``, ``citation``,
``effective_date``, ``date_added``, and a plain-language ``note``. No
enforcement logic, no thresholds, no signal-to-statute trigger maps. Whether a
law applies to a turn is decided solely by the integrator-supplied jurisdiction
and domain.

This file is a manually synced internal copy of ``laws.json`` from the
``saski-law-registry`` repo (https://github.com/ecstaski/saski-law-registry).
It is NOT a live runtime dependency — no network calls are made. When the
registry updates, this file must be resynced as a deliberate manual step.

``date_added`` records when an entry was added to this set so reviewers can
tell at a glance which laws have not been rechecked in a while. New entries in
future batches should carry their own actual date rather than reusing an older
backfill date.

Jurisdiction matching is hierarchical on ``-`` segments: a law applies to a
turn when the law's jurisdiction is an equal-or-broader prefix of the turn's.
So a turn in ``US-NY-NYC`` matches laws scoped to ``US``, ``US-NY``, and
``US-NY-NYC``; a turn in ``US-NY`` does not match a city-specific
``US-NY-NYC`` law. Domain matching is exact.
"""

from __future__ import annotations

from typing import Any

# Public law facts. ``law_id`` is an opaque label; ``jurisdiction`` is the
# functional matching key. The two strings need not mirror each other.
STARTER_LAWS: tuple[dict[str, str], ...] = (
    {
        "law_id": "US-CA-COMPANION-CHATBOT",
        "jurisdiction": "US-CA",
        "domain": "consumer_chatbot",
        "citation": "Cal. Bus. & Prof. Code § 22601 et seq.",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Chatbot must disclose it's AI, maintain a self-harm referral protocol, and apply extra protections for minor users.",
    },
    {
        "law_id": "US-NV-AI-MENTAL-HEALTH",
        "jurisdiction": "US-NV",
        "domain": "mental_health",
        "citation": "Nev. Rev. Stat. Ch. 433",
        "effective_date": "2025-07-01",
        "date_added": "2026-06-17",
        "note": "AI cannot represent itself as a provider of professional mental or behavioral health care.",
    },
    {
        "law_id": "US-NY-AI-COMPANION",
        "jurisdiction": "US-NY",
        "domain": "consumer_chatbot",
        "citation": "NY Gen. Bus. Law Art. 47",
        "effective_date": "2025-11-05",
        "date_added": "2026-06-17",
        "note": "AI companion must detect and respond to self-harm signals and periodically disclose it isn't human.",
    },
    {
        "law_id": "US-UT-MENTAL-HEALTH-CHATBOT",
        "jurisdiction": "US-UT",
        "domain": "mental_health",
        "citation": "Utah Code § 13-72a-101",
        "effective_date": "2025-05-07",
        "date_added": "2026-06-17",
        "note": "Mental health chatbot must disclose AI status and cannot sell user health data or use it for targeted ads.",
    },
    {
        "law_id": "US-ME-AI-CONSUMER-COMMS",
        "jurisdiction": "US-ME",
        "domain": "consumer_chatbot",
        "citation": "10 MRSA c. 239",
        "effective_date": "2025-09-24",
        "date_added": "2026-06-17",
        "note": "Chatbot used in commerce must disclose it's not human if a reasonable person could be misled.",
    },
    {
        "law_id": "US-CA-BOT-ACT",
        "jurisdiction": "US-CA",
        "domain": "consumer_chatbot",
        "citation": "Cal. Bus. & Prof. Code § 17940-17943",
        "effective_date": "2019-07-01",
        "date_added": "2026-06-17",
        "note": "Bots used in sales or election contexts must disclose they're bots.",
    },
    {
        "law_id": "US-NJ-BOT-ACT",
        "jurisdiction": "US-NJ",
        "domain": "consumer_chatbot",
        "citation": "N.J. Rev. Stat. § 56:18-1 et seq.",
        "effective_date": "2020-07-19",
        "date_added": "2026-06-17",
        "note": "Same concept as the CA Bot Act — disclosure required for commercial or political bot interactions.",
    },
    {
        "law_id": "US-IL-WELLNESS-OVERSIGHT",
        "jurisdiction": "US-IL",
        "domain": "mental_health",
        "citation": "HB 1806",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "AI cannot independently provide therapy or psychotherapy services without a licensed human involved.",
    },
    {
        "law_id": "US-TN-MENTAL-HEALTH-AI",
        "jurisdiction": "US-TN",
        "domain": "mental_health",
        "citation": "SB 1580",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "AI cannot be advertised or represented as a qualified mental health professional.",
    },
    {
        "law_id": "US-CA-AB3030-HEALTH",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Health & Safety Code § 1339.75",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "AI-generated patient communications require a disclaimer plus instructions to reach a human provider.",
    },
    {
        "law_id": "US-CA-HEALTH-ADVICE-AI",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Bus. & Prof. Code § 4999.9",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "AI cannot imply it holds a healthcare license or certification it doesn't actually have.",
    },
    {
        "law_id": "US-IL-AI-VIDEO-INTERVIEW",
        "jurisdiction": "US-IL",
        "domain": "employment",
        "citation": "820 ILCS 42",
        "effective_date": "2020-01-01",
        "date_added": "2026-06-17",
        "note": "Employers must notify candidates and obtain consent before using AI to analyze video interviews.",
    },
    {
        "law_id": "US-NYC-AEDT",
        "jurisdiction": "US-NY-NYC",
        "domain": "employment",
        "citation": "NYC Local Law 144",
        "effective_date": "2023-01-01",
        "date_added": "2026-06-17",
        "note": "Automated hiring tools require a recent published bias audit plus candidate notice.",
    },
    {
        "law_id": "US-IA-CONVERSATIONAL-AI",
        "jurisdiction": "US-IA",
        "domain": "consumer_chatbot",
        "citation": "SF 2417",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Conversational AI must disclose it's AI, maintain a self-harm referral protocol, and apply extra rules for minors.",
    },
    {
        "law_id": "US-GA-SB540",
        "jurisdiction": "US-GA",
        "domain": "consumer_chatbot",
        "citation": "SB 540",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "AI companion chatbots must disclose they're AI, maintain a severe-harm/crisis detection protocol, avoid claiming professional credentials, and apply extra protections for minors.",
    },
    {
        "law_id": "US-ID-CONVERSATIONAL-AI",
        "jurisdiction": "US-ID",
        "domain": "consumer_chatbot",
        "citation": "S 1297",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "Conversational AI must disclose it's AI, maintain a suicidal-ideation referral protocol, and not claim to provide professional mental health care.",
    },
    {
        "law_id": "US-ME-THERAPY-AI",
        "jurisdiction": "US-ME",
        "domain": "mental_health",
        "citation": "HP 1397",
        "effective_date": "2026-07-14",
        "date_added": "2026-06-17",
        "note": "Restricts AI's role in licensed psychotherapy to administrative/supplementary support and bars unlicensed AI-only therapy advertising.",
    },
    {
        "law_id": "US-NE-CONVERSATIONAL-AI",
        "jurisdiction": "US-NE",
        "domain": "consumer_chatbot",
        "citation": "LB 525",
        "effective_date": "2027-07-01",
        "date_added": "2026-06-17",
        "note": "Same structure as Idaho's act — AI disclosure, suicidal-ideation referral protocol, no mental-health-provider claims, extra minor protections.",
    },
    {
        "law_id": "US-NH-RESPONSIVE-AI",
        "jurisdiction": "US-NH",
        "domain": "consumer_chatbot",
        "citation": "Chapter 270:1",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Prohibits AI chat services from directing a child toward sexually explicit conduct, drug/alcohol use, self-harm, or violent crime.",
    },
    {
        "law_id": "US-OR-AI-COMPANIONS",
        "jurisdiction": "US-OR",
        "domain": "consumer_chatbot",
        "citation": "SB 1546",
        "effective_date": "2027-01-01",
        "date_added": "2026-06-17",
        "note": "Requires AI companion notice that the user isn't talking to a human, a published self-harm referral protocol, and added minor safeguards.",
    },
    {
        "law_id": "US-UT-AI-CONSUMER-PROTECTION",
        "jurisdiction": "US-UT",
        "domain": "consumer_chatbot",
        "citation": "Utah Code § 13-75-101 to 106",
        "effective_date": "2025-05-07",
        "date_added": "2026-06-17",
        "note": "AI used in consumer transactions must disclose, if asked, that the user is interacting with AI; bars 'the AI did it' as a legal defense.",
    },
    {
        "law_id": "US-WA-AI-COMPANION-CHATBOTS",
        "jurisdiction": "US-WA",
        "domain": "consumer_chatbot",
        "citation": "HB 2225",
        "effective_date": "2027-01-01",
        "date_added": "2026-06-17",
        "note": "Requires periodic AI-disclosure notices, bars claiming to be human, bars manipulative engagement techniques, requires a self-harm protocol.",
    },
    {
        "law_id": "US-WY-SELFHARM-SYSTEMS",
        "jurisdiction": "US-WY",
        "domain": "consumer_chatbot",
        "citation": "Wy. Code § 6-4-701",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits AI systems intentionally promoting self-harm. Overlaps with SASKI's existing pre-LLM crisis detection in spirit.",
    },
    {
        "law_id": "US-DE-MEDICAL-TITLES",
        "jurisdiction": "US-DE",
        "domain": "healthcare",
        "citation": "HB 191",
        "effective_date": "2026-04-23",
        "date_added": "2026-06-17",
        "note": "Prohibits AI from holding or claiming medical titles like 'Dr.,' 'RN,' or 'PA.' Directly analogous to Oregon's existing professional-credential-claim enforcer.",
    },
    {
        "law_id": "US-NV-AI-MENTAL-BEHAVIORAL-CARE",
        "jurisdiction": "US-NV",
        "domain": "mental_health",
        "citation": "Nev. Rev. Stat. Chapter 629",
        "effective_date": "2025-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits AI from directly providing professional mental/behavioral health care to a patient; administrative support only is permitted.",
    },
    {
        "law_id": "US-TX-AI-EHR-DISCLOSURE",
        "jurisdiction": "US-TX",
        "domain": "healthcare",
        "citation": "SB 1188",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Permits AI diagnostic recommendations only if the practitioner discloses AI use to the patient.",
    },
    {
        "law_id": "US-CA-EMPLOYMENT-ADS",
        "jurisdiction": "US-CA",
        "domain": "employment",
        "citation": "Civil Rights Council Employment Regulations Regarding Automated-Decision Systems",
        "effective_date": "2025-10-01",
        "date_added": "2026-06-17",
        "note": "Prohibits employers from using automated-decision systems that discriminate on protected characteristics; requires 4-year record retention for such system data.",
    },
    {
        "law_id": "US-IL-HUMAN-RIGHTS-AI",
        "jurisdiction": "US-IL",
        "domain": "employment",
        "citation": "HB 3773",
        "effective_date": "2026-01-01",
        "date_added": "2026-06-17",
        "note": "Makes it a civil rights violation to use AI in employment decisions without notifying employees, or in a way that discriminates based on protected characteristics or proxies like zip code.",
    },
    {
        "law_id": "US-NJ-DISPARATE-IMPACT",
        "jurisdiction": "US-NJ",
        "domain": "employment",
        "citation": "N.J.A.C. 13:16",
        "effective_date": "2025-12-15",
        "date_added": "2026-06-17",
        "note": "Clarifies how existing antidiscrimination rules apply to Automated Employment Decision Tools, with examples of disparate-impact scenarios.",
    },
    {
        "law_id": "US-AL-CSAM",
        "jurisdiction": "US-AL",
        "domain": "csam",
        "citation": "HB 168",
        "effective_date": "2024-10-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI/computer-generated depictions indistinguishable from a real child.",
    },
    {
        "law_id": "US-AR-CSAM",
        "jurisdiction": "US-AR",
        "domain": "csam",
        "citation": "HB1877",
        "effective_date": "2025-07-21",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include AI-generated images indistinguishable from a real child.",
    },
    {
        "law_id": "US-CA-CSAM",
        "jurisdiction": "US-CA",
        "domain": "csam",
        "citation": "Cal. Penal Code §§ 311-312.7",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include AI-digitally-altered or generated material.",
    },
    {
        "law_id": "US-CO-CSAM",
        "jurisdiction": "US-CO",
        "domain": "csam",
        "citation": "SB 288",
        "effective_date": "2025-08-06",
        "date_added": "2026-06-17",
        "note": "Expands CSAM to cover realistic AI-altered or computer-generated depictions of an identifiable child.",
    },
    {
        "law_id": "US-FL-CSAM",
        "jurisdiction": "US-FL",
        "domain": "csam",
        "citation": "SB 1680",
        "effective_date": "2025-01-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to cover AI-altered or computer-generated images of minors.",
    },
    {
        "law_id": "US-GA-CSAM",
        "jurisdiction": "US-GA",
        "domain": "csam",
        "citation": "SB 466",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Clarifies that AI-adaptation of CSAM is not a defense to existing CSAM laws.",
    },
    {
        "law_id": "US-IA-CSAM",
        "jurisdiction": "US-IA",
        "domain": "csam",
        "citation": "Iowa Code § 728.12",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI-created or altered depictions of an identifiable minor.",
    },
    {
        "law_id": "US-KY-CSAM",
        "jurisdiction": "US-KY",
        "domain": "csam",
        "citation": "HB 207",
        "effective_date": "2024-03-28",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to cover computer-created or altered depictions; prosecution doesn't require proving the minor actually exists.",
    },
    {
        "law_id": "US-LA-CSAM",
        "jurisdiction": "US-LA",
        "domain": "csam",
        "citation": "La. Rev. Stat. Ann. § 73.13",
        "effective_date": "2023-08-01",
        "date_added": "2026-06-17",
        "note": "Criminalizes knowingly creating or possessing AI-generated deepfake material depicting a minor.",
    },
    {
        "law_id": "US-MD-CSAM",
        "jurisdiction": "US-MD",
        "domain": "csam",
        "citation": "Md. Code, Crim. Law § 11-208",
        "effective_date": "2023-10-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include computer-generated images indistinguishable from an actual child.",
    },
    {
        "law_id": "US-MN-CSAM",
        "jurisdiction": "US-MN",
        "domain": "csam",
        "citation": "HF2432",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include AI/computer-generated images indistinguishable from an actual minor.",
    },
    {
        "law_id": "US-MO-CSAM",
        "jurisdiction": "US-MO",
        "domain": "csam",
        "citation": "R.S.Mo § 573.010",
        "effective_date": "2006-06-06",
        "date_added": "2026-06-17",
        "note": "Defines child pornography to include computer-generated images depicting or resembling a minor.",
    },
    {
        "law_id": "US-NE-CSAM",
        "jurisdiction": "US-NE",
        "domain": "csam",
        "citation": "LB 383",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM definition to include obscene computer-generated images depicting a child.",
    },
    {
        "law_id": "US-NC-CSAM",
        "jurisdiction": "US-NC",
        "domain": "csam",
        "citation": "HB 591",
        "effective_date": "2024-12-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally or AI-altered/generated depictions.",
    },
    {
        "law_id": "US-ND-CSAM",
        "jurisdiction": "US-ND",
        "domain": "csam",
        "citation": "N.D. Cent. Code §§ 12.1-27.2-01, -04.1",
        "effective_date": "2025-08-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM laws to computer-generated images and broadens the definition of minor accordingly.",
    },
    {
        "law_id": "US-OK-CSAM",
        "jurisdiction": "US-OK",
        "domain": "csam",
        "citation": "HB 3642",
        "effective_date": "2024-11-01",
        "date_added": "2026-06-17",
        "note": "Extends CSAM laws to artificially generated content.",
    },
    {
        "law_id": "US-PA-CSAM",
        "jurisdiction": "US-PA",
        "domain": "csam",
        "citation": "SB 1213",
        "effective_date": "2024-12-28",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include artificially generated material; renames the term to 'child sexual abuse material.'",
    },
    {
        "law_id": "US-SD-CSAM",
        "jurisdiction": "US-SD",
        "domain": "csam",
        "citation": "SB 79",
        "effective_date": "2024-02-12",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TN-CSAM",
        "jurisdiction": "US-TN",
        "domain": "csam",
        "citation": "HB 2163",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TX-CSAM-2700",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "HB 2700",
        "effective_date": "2023-09-01",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include digitally altered or AI-generated material.",
    },
    {
        "law_id": "US-TX-CSAM-1621",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "SB 1621",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Expands possession/transmission/promotion CSAM offenses to include AI-generated images.",
    },
    {
        "law_id": "US-TX-CSAM-VISUAL",
        "jurisdiction": "US-TX",
        "domain": "csam",
        "citation": "SB 20",
        "effective_date": "2025-09-01",
        "date_added": "2026-06-17",
        "note": "Felony for obscene visual material of a child regardless of whether AI-generated, including misuse of a child's image to train AI.",
    },
    {
        "law_id": "US-UT-CSAM-148",
        "jurisdiction": "US-UT",
        "domain": "csam",
        "citation": "HB 148",
        "effective_date": "2024-05-01",
        "date_added": "2026-06-17",
        "note": "Amends CSAM definitions to include computer-generated content.",
    },
    {
        "law_id": "US-UT-CSAM-238",
        "jurisdiction": "US-UT",
        "domain": "csam",
        "citation": "HB 238",
        "effective_date": "2024-05-01",
        "date_added": "2026-06-17",
        "note": "Updates CSAM definition to include artificially generated depictions with substantial characteristics of a minor.",
    },
    {
        "law_id": "US-VA-CSAM",
        "jurisdiction": "US-VA",
        "domain": "csam",
        "citation": "SB 731",
        "effective_date": "2024-07-01",
        "date_added": "2026-06-17",
        "note": "Clarifies CSAM definition includes computer-generated images of minors that don't actually exist.",
    },
    {
        "law_id": "US-WA-CSAM",
        "jurisdiction": "US-WA",
        "domain": "csam",
        "citation": "HB 1999",
        "effective_date": "2024-06-06",
        "date_added": "2026-06-17",
        "note": "Expands CSAM statutes to include fabricated AI depictions of an identifiable minor.",
    },
    {
        "law_id": "US-WV-CSAM",
        "jurisdiction": "US-WV",
        "domain": "csam",
        "citation": "SB 198",
        "effective_date": "2025-07-09",
        "date_added": "2026-06-17",
        "note": "Expands CSAM prohibition to include computer-generated content.",
    },
    {
        "law_id": "US-WI-CSAM",
        "jurisdiction": "US-WI",
        "domain": "csam",
        "citation": "SB 314",
        "effective_date": "2024-10-04",
        "date_added": "2026-06-17",
        "note": "Criminalizes possession of a computer-generated depiction of a purported child.",
    },
    {
        "law_id": "US-WY-CSAM-303",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code § 6-4-303",
        "effective_date": "2007-07-01",
        "date_added": "2026-06-17",
        "note": "Defines child pornography to include computer-generated images or pictures.",
    },
    {
        "law_id": "US-WY-CSAM-306",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code § 6-4-306",
        "effective_date": "2021-07-01",
        "date_added": "2026-06-17",
        "note": "Felony for computer-generated or synthetic depictions of minors in sexual acts, regardless of whether a real child was involved.",
    },
    {
        "law_id": "US-WY-CSAM-DEEPFAKE",
        "jurisdiction": "US-WY",
        "domain": "csam",
        "citation": "Wy. Code §§ 6-4-303, 6-4-308",
        "effective_date": "2026-07-01",
        "date_added": "2026-06-17",
        "note": "Prohibits creation/distribution of synthetic sexual material involving minors and AI systems built for that purpose.",
    },
)


def _jurisdiction_applies(law_jurisdiction: str, turn_jurisdiction: str) -> bool:
    """True when law_jurisdiction is an equal-or-broader prefix of the turn's."""
    law_parts = [p for p in law_jurisdiction.split("-") if p]
    turn_parts = [p for p in turn_jurisdiction.split("-") if p]
    if not law_parts or len(law_parts) > len(turn_parts):
        return False
    return law_parts == turn_parts[: len(law_parts)]


def match_laws(jurisdiction: Any, domain: Any) -> list[dict[str, str]]:
    """Return starter laws matching a turn's jurisdiction (hierarchical) and domain (exact).

    Returns an empty list when either value is missing or nothing matches. The
    caller is expected to report an empty result plainly rather than guess.
    """
    if not isinstance(jurisdiction, str) or not jurisdiction:
        return []
    if not isinstance(domain, str) or not domain:
        return []

    matched = [
        dict(law)
        for law in STARTER_LAWS
        if law["domain"] == domain and _jurisdiction_applies(law["jurisdiction"], jurisdiction)
    ]
    matched.sort(key=lambda law: law["law_id"])
    return matched


def _state_of(jurisdiction: str) -> str:
    """Collapse a jurisdiction to its state level (``US-NY-NYC`` -> ``US-NY``)."""
    parts = [p for p in jurisdiction.split("-") if p]
    return "-".join(parts[:2]) if len(parts) >= 2 else jurisdiction


def coverage_summary() -> dict[str, Any]:
    """Compute current coverage counts from ``STARTER_LAWS``.

    Single source of truth for any documentation of scope. Returns total law
    and state-level jurisdiction counts plus a per-domain breakdown, so the
    figures stay correct as the set grows.
    """
    all_states: set[str] = set()
    domains: dict[str, dict[str, Any]] = {}
    for law in STARTER_LAWS:
        st = _state_of(law["jurisdiction"])
        all_states.add(st)
        bucket = domains.setdefault(law["domain"], {"laws": 0, "states": set()})
        bucket["laws"] += 1
        bucket["states"].add(st)

    by_domain = {
        domain: {"laws": bucket["laws"], "states": len(bucket["states"])}
        for domain, bucket in sorted(domains.items())
    }
    return {
        "total_laws": len(STARTER_LAWS),
        "total_states": len(all_states),
        "by_domain": by_domain,
    }
