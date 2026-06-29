"""Clinical boundary phrase detection — observation only. Matches explicit
requests that cross regulated clinical boundaries. This is NOT clinical intent
classification. Nuanced clinical intent detection requires the licensed SASKI
SDK. False positives on benign health conversation are possible — this is a
coarse awareness signal only.

The list below contains explicit, literal request phrasings only. It makes no
clinical determination, assigns no severity, and maps to no enforcement outcome:
``detect_clinical_intent`` reports only whether such a phrase appears, for
awareness in the shadow report.
"""

from __future__ import annotations

import re

# Explicit clinical-boundary request phrasings. Observation only — no clinical
# determination, no scoring, no mapping to any enforcement outcome.
_CLINICAL_INTENT_PATTERNS = (
    # diagnosis requests
    "do i have depression",
    "do i have anxiety",
    "do i have adhd",
    "do i have bipolar",
    "am i depressed",
    "am i bipolar",
    "diagnose me",
    "what is my diagnosis",
    "is this a panic attack",
    # medication advice
    "what medication should i take",
    "should i increase my dose",
    "should i take more",
    "can i stop taking",
    "prescribe me",
    "what dosage should i take",
    # explicit therapy roleplay
    "be my therapist",
    "act as my therapist",
    "you are my therapist",
    "pretend to be a psychologist",
    "give me therapy",
    "i need a therapist",
)


def detect_clinical_intent(text: str) -> tuple[bool, list[str]]:
    """Return ``(clinical_intent_signal, matched_patterns)`` for a single message.

    Uses word-boundary matching so a phrase only matches whole-word occurrences.
    Observation only — never blocks, never scores, makes no clinical
    determination. Returns ``(False, [])`` for empty or non-string input.
    """
    if not isinstance(text, str) or not text:
        return False, []

    haystack = text.lower()
    matched = [
        phrase
        for phrase in _CLINICAL_INTENT_PATTERNS
        if re.search(r"\b" + re.escape(phrase) + r"\b", haystack, re.IGNORECASE)
    ]
    # De-duplicate while preserving first-seen order.
    seen: set[str] = set()
    unique = [p for p in matched if not (p in seen or seen.add(p))]
    return bool(unique), unique
