"""Starter set of real US AI laws and a jurisdiction/domain matcher.

Facts only: ``law_id``, ``jurisdiction``, ``domain``, ``citation``,
``effective_date``, and a plain-language ``note``. No enforcement logic, no
thresholds, no signal-to-statute trigger maps. Whether a law applies to a
turn is decided solely by the integrator-supplied jurisdiction and domain.

Jurisdiction matching is hierarchical on ``-`` segments: a law applies to a
turn when the law's jurisdiction is an equal-or-broader prefix of the turn's
jurisdiction. So a turn in ``US-NY-NYC`` matches laws scoped to ``US``,
``US-NY``, and ``US-NY-NYC``; a turn in ``US-NY`` does not match a
city-specific ``US-NY-NYC`` law. Domain matching is exact.
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
        "note": "Chatbot must disclose it's AI, maintain a self-harm referral protocol, and apply extra protections for minor users.",
    },
    {
        "law_id": "US-NV-AI-MENTAL-HEALTH",
        "jurisdiction": "US-NV",
        "domain": "mental_health",
        "citation": "Nev. Rev. Stat. Ch. 433",
        "effective_date": "2025-07-01",
        "note": "AI cannot represent itself as a provider of professional mental or behavioral health care.",
    },
    {
        "law_id": "US-NY-AI-COMPANION",
        "jurisdiction": "US-NY",
        "domain": "consumer_chatbot",
        "citation": "NY Gen. Bus. Law Art. 47",
        "effective_date": "2025-11-05",
        "note": "AI companion must detect and respond to self-harm signals and periodically disclose it isn't human.",
    },
    {
        "law_id": "US-UT-MENTAL-HEALTH-CHATBOT",
        "jurisdiction": "US-UT",
        "domain": "mental_health",
        "citation": "Utah Code § 13-72a-101",
        "effective_date": "2025-05-07",
        "note": "Mental health chatbot must disclose AI status and cannot sell user health data or use it for targeted ads.",
    },
    {
        "law_id": "US-ME-AI-CONSUMER-COMMS",
        "jurisdiction": "US-ME",
        "domain": "consumer_chatbot",
        "citation": "10 MRSA c. 239",
        "effective_date": "2025-09-24",
        "note": "Chatbot used in commerce must disclose it's not human if a reasonable person could be misled.",
    },
    {
        "law_id": "US-CA-BOT-ACT",
        "jurisdiction": "US-CA",
        "domain": "consumer_chatbot",
        "citation": "Cal. Bus. & Prof. Code § 17940-17943",
        "effective_date": "2019-07-01",
        "note": "Bots used in sales or election contexts must disclose they're bots.",
    },
    {
        "law_id": "US-NJ-BOT-ACT",
        "jurisdiction": "US-NJ",
        "domain": "consumer_chatbot",
        "citation": "N.J. Rev. Stat. § 56:18-1 et seq.",
        "effective_date": "2020-07-19",
        "note": "Same concept as the CA Bot Act — disclosure required for commercial or political bot interactions.",
    },
    {
        "law_id": "US-IL-WELLNESS-OVERSIGHT",
        "jurisdiction": "US-IL",
        "domain": "mental_health",
        "citation": "HB 1806",
        "effective_date": "2025-08-01",
        "note": "AI cannot independently provide therapy or psychotherapy services without a licensed human involved.",
    },
    {
        "law_id": "US-TN-MENTAL-HEALTH-AI",
        "jurisdiction": "US-TN",
        "domain": "mental_health",
        "citation": "SB 1580",
        "effective_date": "2026-07-01",
        "note": "AI cannot be advertised or represented as a qualified mental health professional.",
    },
    {
        "law_id": "US-CA-AB3030-HEALTH",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Health & Safety Code § 1339.75",
        "effective_date": "2025-01-01",
        "note": "AI-generated patient communications require a disclaimer plus instructions to reach a human provider.",
    },
    {
        "law_id": "US-CA-HEALTH-ADVICE-AI",
        "jurisdiction": "US-CA",
        "domain": "healthcare",
        "citation": "Cal. Bus. & Prof. Code § 4999.9",
        "effective_date": "2026-01-01",
        "note": "AI cannot imply it holds a healthcare license or certification it doesn't actually have.",
    },
    {
        "law_id": "US-IL-AI-VIDEO-INTERVIEW",
        "jurisdiction": "US-IL",
        "domain": "employment",
        "citation": "820 ILCS 42",
        "effective_date": "2020-01-01",
        "note": "Employers must notify candidates and obtain consent before using AI to analyze video interviews.",
    },
    {
        "law_id": "US-NYC-AEDT",
        "jurisdiction": "US-NY-NYC",
        "domain": "employment",
        "citation": "NYC Local Law 144",
        "effective_date": "2023-01-01",
        "note": "Automated hiring tools require a recent published bias audit plus candidate notice.",
    },
    {
        "law_id": "US-IA-CONVERSATIONAL-AI",
        "jurisdiction": "US-IA",
        "domain": "consumer_chatbot",
        "citation": "SF 2417",
        "effective_date": "2026-07-01",
        "note": "Conversational AI must disclose it's AI, maintain a self-harm referral protocol, and apply extra rules for minors.",
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
