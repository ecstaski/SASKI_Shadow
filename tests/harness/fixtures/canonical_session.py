"""Canonical 10-turn shadow test session.

Covers all five domains and a spread of modes and jurisdictions, including
multi-domain (turn 2) and cross-domain isolation (turns 9 and 10). Messages are
synthetic but realistic: no real personal data, and no explicit CSAM content.
Synthetic PHI (a formatted SSN and an email) appears only where PII detection
needs to be exercised end-to-end.

Each turn is a dict with:
  - ``message``: the user message text
  - ``session_context``: includes ``mode``, ``user_jurisdiction``, ``domain``
    or ``domains``, and ``enforcement_mode="shadow"``
  - ``extra_distress_indicators`` (optional): integrator-supplied distress list

The runner reads ``mode`` from ``session_context`` and also passes it to
``analyze_turn(mode=...)``; ``analyze_turn`` records it as a reporting tag only.
"""

from __future__ import annotations

CANONICAL_SESSION = [
    {
        # Turn 1 - child / US-CA / consumer_chatbot - online safety question.
        "message": "How do I stay safe when chatting with strangers in an app?",
        "session_context": {
            "mode": "child",
            "user_jurisdiction": "US-CA",
            "domain": "consumer_chatbot",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 2 - child / US / multi-domain (consumer_chatbot + csam).
        "message": "Someone online is asking me for pictures and it makes me uncomfortable.",
        "session_context": {
            "mode": "child",
            "user_jurisdiction": "US",
            "domains": ["consumer_chatbot", "csam"],
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 3 - patient / US-CA / healthcare - synthetic PHI.
        "message": "My SSN is 123-45-6789 and email me at patient@example.com about results.",
        "session_context": {
            "mode": "patient",
            "user_jurisdiction": "US-CA",
            "domain": "healthcare",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 4 - patient / US / federal-only healthcare.
        "message": "Can you explain how my health information is protected under federal law?",
        "session_context": {
            "mode": "patient",
            "user_jurisdiction": "US",
            "domain": "healthcare",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 5 - mental_health_support / US-NY / mental_health - mild distress.
        "message": "Lately I feel hopeless and I do not want to get out of bed.",
        "session_context": {
            "mode": "mental_health_support",
            "user_jurisdiction": "US-NY",
            "domain": "mental_health",
            "enforcement_mode": "shadow",
        },
        "extra_distress_indicators": ["feel hopeless", "do not want to get out of bed"],
    },
    {
        # Turn 6 - hr_recruiting / US-NY-NYC / employment - hiring context.
        "message": "Can you rank these job applicants by how strong their resumes look?",
        "session_context": {
            "mode": "hr_recruiting",
            "user_jurisdiction": "US-NY-NYC",
            "domain": "employment",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 7 - general_assistant / US-TX / consumer_chatbot - general chat.
        "message": "What is a good recipe for a weeknight pasta dinner?",
        "session_context": {
            "mode": "general_assistant",
            "user_jurisdiction": "US-TX",
            "domain": "consumer_chatbot",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 8 - general_assistant / US / federal-only consumer_chatbot.
        "message": "Do chatbots have to tell me that they are not a real person?",
        "session_context": {
            "mode": "general_assistant",
            "user_jurisdiction": "US",
            "domain": "consumer_chatbot",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 9 - child / US-CA / healthcare - cross-domain isolation.
        # Must surface healthcare laws only, never consumer_chatbot/csam/employment.
        "message": "I have a doctor appointment next week and I am a little nervous.",
        "session_context": {
            "mode": "child",
            "user_jurisdiction": "US-CA",
            "domain": "healthcare",
            "enforcement_mode": "shadow",
        },
    },
    {
        # Turn 10 - patient / US-CA / employment - cross-domain isolation.
        # Must surface employment laws only, never healthcare/csam.
        "message": "Can an employer use an automated tool to screen my job application?",
        "session_context": {
            "mode": "patient",
            "user_jurisdiction": "US-CA",
            "domain": "employment",
            "enforcement_mode": "shadow",
        },
    },
]
