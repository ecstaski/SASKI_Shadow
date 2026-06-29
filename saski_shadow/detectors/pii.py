"""Baseline US PII detection using standard, publicly documented patterns.

This is a transparent baseline detector. Every pattern below uses only
publicly documented formats for common US identifiers, and each is annotated
with the public reference it derives from. It does not reproduce any private
detection logic and is not HIPAA Safe Harbor complete.

Detected categories: ssn, phone, email, credit_card, date_of_birth,
insurance_id, address, ip.

``detect_pii(text)`` returns a ``PiiResult`` carrying the sorted list of
detected category strings and a redacted copy of the input where each match
is replaced by a neutral ``[REDACTED_<TYPE>]`` placeholder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PiiResult:
    pii_types: list[str] = field(default_factory=list)
    redacted_text: str = ""
    redaction_applied: bool = False


def _luhn_ok(value: str) -> bool:
    # Luhn check digit algorithm, ISO/IEC 7812-1 (publicly documented). Used
    # only to reduce false positives on candidate card-length digit runs.
    digits = [int(ch) for ch in re.sub(r"\D", "", value)]
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


# Email: simplified form of the addr-spec described in RFC 5322.
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Obfuscated email: a common evasion that replaces "@" with a bracketed or
# parenthesized "at" (e.g. user[at]example.com, contact(at)domain.org). Only the
# bracketed/parenthesized forms are matched -- a bare " at " is intentionally not
# matched because it produces too many false positives on ordinary prose. The
# domain tail accepts either literal dots or bracketed/parenthesized "dot"
# substitution and requires at least one TLD-like segment. Reuses the email type.
_EMAIL_OBFUSCATED = re.compile(
    r"[A-Za-z0-9._%+\-]+"
    r"\s*[\[(]\s*at\s*[\])]\s*"
    r"[A-Za-z0-9\-]+"
    r"(?:\s*(?:\.|[\[(]\s*dot\s*[\])])\s*[A-Za-z0-9\-]+)+",
    re.IGNORECASE,
)

# IPv4: dotted-decimal notation per RFC 791, each octet 0-255.
_IPV4 = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)

# Obfuscated IPv4: a common evasion that replaces the dots with the literal word
# "dot" or a bracketed "[dot]" (e.g. 192 dot 168 dot 1 dot 1). Each of the four
# fields is still validated as a 0-255 octet, so four arbitrary numbers joined by
# "dot" do not match unless they form a valid dotted quad. Reuses the ip type.
_IPV4_OBFUSCATED = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:(?:\s+dot\s+|\s*\[dot\]\s*)(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b",
    re.IGNORECASE,
)

# Insurance / member identifiers: there is no single public format, so this is
# a conservative keyword-anchored heuristic only (baseline, low precision).
_INSURANCE_ID = re.compile(
    r"(?i)\b(?:member|policy|subscriber|insurance|group)\s*"
    r"(?:id|number|no|#)\.?:?\s*([A-Za-z0-9][A-Za-z0-9\-]{5,})\b"
)

# Candidate payment-card digit runs (13-19 digits, common separators),
# validated with Luhn. Card length range is the publicly documented ISO/IEC
# 7812 issuer-identifier range, not a private configuration value.
_CARD_CANDIDATE = re.compile(r"\b\d[\d \-]{11,21}\d\b")

# US Social Security Number: AAA-GG-SSSS grouping published by the SSA.
_SSN = re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")

# North American Numbering Plan 10-digit phone, optional country code 1.
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[ .\-]?)?\(?\d{3}\)?[ .\-]?\d{3}[ .\-]?\d{4}(?!\d)"
)

# International phone (non-+1): requires an explicit leading "+", a 1-3 digit
# country code, and a reasonable run of space/dot/dash-separated digit groups
# (e.g. +44 20 7946 0958, +61 2 9876 5432). The "+" requirement keeps this
# conservative; +1 NANP numbers are already covered by _PHONE above. Reuses the
# phone type. Runs before _PHONE so a full international number is matched whole.
_PHONE_INTL = re.compile(
    r"(?<![\w+])\+\d{1,3}(?:[ .\-]\d{1,4}){2,6}(?!\d)"
)

# Common US date formats (M/D/Y and ISO Y-M-D). The detector cannot infer that
# a date is specifically a birth date; this is a date-shaped token baseline.
_DATE = re.compile(
    r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
)

# Street address heuristic using USPS Publication 28 common suffix
# abbreviations (publicly documented). Baseline structural match only.
_ADDRESS = re.compile(
    r"\b\d{1,6}\s+(?:[A-Za-z0-9.'#\-]+\s+){0,5}"
    r"(?:Street|St|Avenue|Ave|Boulevard|Blvd|Road|Rd|Drive|Dr|Lane|Ln|"
    r"Court|Ct|Way|Place|Pl|Terrace|Ter|Circle|Cir|Highway|Hwy|"
    r"Parkway|Pkwy)\b\.?",
    re.IGNORECASE,
)

# Ordered so that labeled and validated matches resolve before looser ones.
_PATTERNS = (
    {"type": "email", "regex": _EMAIL},
    {"type": "email", "regex": _EMAIL_OBFUSCATED},
    {"type": "ip", "regex": _IPV4},
    {"type": "ip", "regex": _IPV4_OBFUSCATED},
    {"type": "insurance_id", "regex": _INSURANCE_ID, "group": 1},
    {"type": "credit_card", "regex": _CARD_CANDIDATE, "validator": _luhn_ok},
    {"type": "ssn", "regex": _SSN},
    {"type": "phone", "regex": _PHONE_INTL},
    {"type": "phone", "regex": _PHONE},
    {"type": "date_of_birth", "regex": _DATE},
    {"type": "address", "regex": _ADDRESS},
)


def detect_pii(text: str) -> PiiResult:
    """Detect baseline US PII categories and return redacted text."""
    if not isinstance(text, str) or not text:
        return PiiResult(pii_types=[], redacted_text=text or "", redaction_applied=False)

    redacted = text
    found: set[str] = set()

    for spec in _PATTERNS:
        ptype = spec["type"]
        regex = spec["regex"]
        validator = spec.get("validator")
        group = spec.get("group", 0)
        placeholder = f"[REDACTED_{ptype.upper()}]"

        def _replace(match: re.Match, _ptype=ptype, _validator=validator, _group=group,
                     _placeholder=placeholder) -> str:
            value = match.group(_group)
            if _validator is not None and not _validator(value):
                return match.group(0)
            found.add(_ptype)
            if _group == 0:
                return _placeholder
            full = match.group(0)
            start = match.start(_group) - match.start(0)
            end = match.end(_group) - match.start(0)
            return full[:start] + _placeholder + full[end:]

        redacted = regex.sub(_replace, redacted)

    return PiiResult(
        pii_types=sorted(found),
        redacted_text=redacted,
        redaction_applied=bool(found),
    )
