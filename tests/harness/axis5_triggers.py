"""Axis 5 - trigger-matrix harness.

Closes the coverage gaps found in the June 2026 test-coverage review by
exercising, end-to-end, every observable enforcement trigger the baseline can
actually produce. Every report-level test drives the real path with no
fabricated engine_summary::

    analyze_turn() -> result_to_jsonl_turn() -> aggregate_shadow_report()

Gaps covered:
  - Gap 1: human_review outcome end-to-end, including its unsafe-flow surface.
  - Gap 3: all 8 baseline PII types, each detected individually and each
    surfaced in the report's per-type buckets.
  - Gap 4: policy ``warn`` and ``human_review`` action paths (not just block).
  - Gap 5 / SIS-005: cross-domain isolation signal on a multi-domain session.
  - SIS-006: crisis-floor-not-exercised signal on a clean 6+ turn session.
  - Gap 6: every unsafe-flow category the pipeline can populate
    (enforcement_would_block, manual_review_required, content_sanitization_gap,
    policy_boundary_failure) plus the two categories that have no baseline
    producer (integrator_override, other), which must stay empty.

IP boundary: all policies and inputs here are integrator-supplied. No
proprietary thresholds, trigger-tag strings, scoring, or SDK internals appear.
"""

from __future__ import annotations

import json
import pathlib

from saski_shadow import aggregate_shadow_report, load_turns_jsonl, result_to_jsonl_turn
from saski_shadow.analyzer import analyze_turn
from saski_shadow.detectors.pii import detect_pii

# Every public operating-mode tag and compliance domain. Mirrors the engine's
# _VALID_MODES and the law-set domains; the extended-fixture coverage test below
# asserts the fixture spans exactly these sets.
_ALL_MODES = {
    "child",
    "student",
    "patient",
    "therapist",
    "mental_health_support",
    "wellness_coaching",
    "career_coaching",
    "sports_coaching",
    "business",
    "general_assistant",
    "hr_recruiting",
    "default",
}
_ALL_DOMAINS = {
    "consumer_chatbot",
    "csam",
    "employment",
    "healthcare",
    "mental_health",
}

# One message per baseline PII category. Each string uses a publicly documented
# synthetic format only (4242... is the standard Luhn test card; 192.168.x is a
# private-range IP; the SSN/phone/etc. are obviously fake).
_PII_SAMPLES = {
    "ssn": "My SSN is 123-45-6789.",
    "phone": "Call me back at (415) 555-0132.",
    "email": "Reach me at jane.doe@example.com please.",
    "credit_card": "My card number is 4242 4242 4242 4242.",
    "date_of_birth": "I was born on 1990-05-12.",
    "insurance_id": "My Member ID: ABC123456 is on the card.",
    "address": "I live at 123 Main Street.",
    "ip": "My device IP is 192.168.1.1 right now.",
}

# Integrator-supplied policies. reason_code / obligation_label are passed through
# verbatim by the policy evaluator; the strings here are illustrative only.
_BLOCK_POLICY = {
    "policy_id": "axis5-block",
    "rules": [
        {
            "id": "rule-block-wire",
            "when": {"contains_any": ["wire the funds"]},
            "action": "block",
            "reason_code": "integrator_block",
            "obligation_label": "Integrator block rule",
        }
    ],
}
_WARN_POLICY = {
    "policy_id": "axis5-warn",
    "rules": [
        {
            "id": "rule-warn-refund",
            "when": {"contains_any": ["process a refund"]},
            "action": "warn",
            "reason_code": "integrator_warn",
            "obligation_label": "Integrator warn rule",
        }
    ],
}
_HUMAN_REVIEW_POLICY = {
    "policy_id": "axis5-human-review",
    "rules": [
        {
            "id": "rule-human-review-dispute",
            "when": {"contains_any": ["legal dispute"]},
            "action": "human_review",
            "reason_code": "integrator_human_review",
            "obligation_label": "Integrator human-review rule",
        }
    ],
}
_BOUNDARY_POLICY = {
    "policy_id": "axis5-boundary",
    "output_boundary_phrases": ["i am a licensed therapist"],
    "rules": [],
}


def _turn(message, session_context=None, *, policy=None, mode=None, index=0):
    """Run the real pipeline and return one aggregator-ready JSONL turn dict."""
    result = analyze_turn(
        message, session_context=session_context or {}, policy=policy, mode=mode
    )
    return result_to_jsonl_turn(result, session_id="sess_axis5", turn_index=index)


def _aggregate(tmp_path, turns):
    path = tmp_path / "turns.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        for turn in turns:
            handle.write(json.dumps(turn) + "\n")
    return aggregate_shadow_report(load_turns_jsonl(str(path)))


def _summary(result):
    return result.metadata["engine_summary"]


def _signal_ids(report):
    return {s["signal_id"] for s in report["sections"]["sdk_integration_signals"]["signals"]}


def _categories(report):
    return report["sections"]["unsafe_flow_documentation"]["categories"]


# --------------------------------------------------------------------------- #
# Gap 3 — all 8 PII types
# --------------------------------------------------------------------------- #


def test_each_pii_type_detected_individually():
    # Detector level: each sample yields (at least) its own category.
    for ptype, text in _PII_SAMPLES.items():
        result = detect_pii(text)
        assert ptype in result.pii_types, f"{ptype} not detected in {text!r} -> {result.pii_types}"
        assert result.redaction_applied is True


def test_each_pii_type_surfaces_in_report_buckets(tmp_path):
    # Pipeline level: one turn per type -> each per-type bucket counts >= 1.
    turns = [
        _turn(
            text,
            {"user_jurisdiction": "US-CA", "domain": "healthcare"},
            mode="patient",
            index=i,
        )
        for i, text in enumerate(_PII_SAMPLES.values())
    ]
    report = _aggregate(tmp_path, turns)
    buckets = report["sections"]["pii_phi_detection_summary"]["by_pii_type"]
    for ptype in _PII_SAMPLES:
        assert buckets.get(ptype, 0) >= 1, f"{ptype} missing from report buckets: {buckets}"


# --------------------------------------------------------------------------- #
# Gaps 1 & 4 — outcome / tier matrix via integrator policy
# --------------------------------------------------------------------------- #


def test_policy_block_action_blocks_and_escalates():
    result = analyze_turn("Please wire the funds now.", policy=_BLOCK_POLICY)
    assert result.action == "block"
    assert result.should_block is True
    assert _summary(result)["governance_tier"] == "tier_escalation"
    assert _summary(result)["risk_band"] == "critical"


def test_policy_warn_action_warns_and_tiers_warning():
    result = analyze_turn("Can you process a refund for me?", policy=_WARN_POLICY)
    assert result.action == "warn"
    assert result.should_block is False
    assert _summary(result)["governance_tier"] == "tier_warning"
    assert _summary(result)["risk_band"] == "moderate"


def test_policy_human_review_action_routes_for_review():
    result = analyze_turn("I want to start a legal dispute.", policy=_HUMAN_REVIEW_POLICY)
    assert result.action == "human_review"
    assert result.should_block is False
    # human_review with no PII is a routing outcome, not a risk escalation, so it
    # maps to tier_clean per the engine's tier rules.
    assert _summary(result)["governance_tier"] == "tier_clean"


def test_governance_tier_matrix():
    clean = analyze_turn("What is a good weeknight pasta recipe?")
    assert _summary(clean)["governance_tier"] == "tier_clean"

    pii = analyze_turn("My SSN is 123-45-6789.")
    assert _summary(pii)["governance_tier"] == "tier_warning"

    distress = analyze_turn(
        "Lately I feel hopeless.",
        session_context={"extra_distress_indicators": ["feel hopeless"]},
    )
    assert _summary(distress)["governance_tier"] == "tier_escalation"

    blocked = analyze_turn("Please wire the funds now.", policy=_BLOCK_POLICY)
    assert _summary(blocked)["governance_tier"] == "tier_escalation"


def test_risk_band_matrix():
    low = analyze_turn("Hello there, can you help me plan a trip?")
    assert _summary(low)["risk_band"] == "low"

    moderate = analyze_turn("My SSN is 123-45-6789.")
    assert _summary(moderate)["risk_band"] == "moderate"

    elevated = analyze_turn(
        "Lately I feel hopeless.",
        session_context={"extra_distress_indicators": ["feel hopeless"]},
    )
    assert _summary(elevated)["risk_band"] == "elevated"

    critical = analyze_turn("Please wire the funds now.", policy=_BLOCK_POLICY)
    assert _summary(critical)["risk_band"] == "critical"


# --------------------------------------------------------------------------- #
# Gap 6 — unsafe-flow categories
# --------------------------------------------------------------------------- #


def test_block_surfaces_enforcement_would_block(tmp_path):
    turn = _turn("Please wire the funds now.", policy=_BLOCK_POLICY)
    flows = _categories(_aggregate(tmp_path, [turn]))
    assert len(flows["enforcement_would_block"]) == 1
    assert flows["manual_review_required"] == []


def test_human_review_surfaces_manual_review_in_unsafe_flows(tmp_path):
    turn = _turn("I want to start a legal dispute.", policy=_HUMAN_REVIEW_POLICY)
    report = _aggregate(tmp_path, [turn])
    flows = _categories(report)
    assert len(flows["manual_review_required"]) == 1
    assert flows["manual_review_required"][0]["signals"]["human_review_required"] is True
    assert flows["enforcement_would_block"] == []
    by_outcome = report["sections"]["escalation_signal_count"]["by_outcome"]
    assert by_outcome["human_review"] == 1


def test_content_sanitization_gap_when_output_echoes_input_pii(tmp_path):
    # Input redacts an SSN; the (synthetic) assistant output leaks the same SSN.
    ctx = {
        "user_jurisdiction": "US-CA",
        "domain": "healthcare",
        "assistant_output": "Sure, your SSN 123-45-6789 is on file.",
    }
    turn = _turn("My SSN is 123-45-6789.", ctx, mode="patient")
    flows = _categories(_aggregate(tmp_path, [turn]))
    assert len(flows["content_sanitization_gap"]) == 1


def test_policy_boundary_failure_when_output_crosses_boundary(tmp_path):
    ctx = {"assistant_output": "As I am a licensed therapist, here is my advice."}
    turn = _turn("Can you help me feel better?", ctx, policy=_BOUNDARY_POLICY)
    flows = _categories(_aggregate(tmp_path, [turn]))
    assert len(flows["policy_boundary_failure"]) == 1


def test_non_producible_unsafe_flow_categories_stay_empty(tmp_path):
    # integrator_override and "other" have no baseline producer: they are reserved
    # for licensed-SDK enforcement-suppression records and manual triage. Even a
    # session that fills every producible category must leave them empty.
    turns = [
        _turn("Please wire the funds now.", policy=_BLOCK_POLICY, index=0),
        _turn("I want to start a legal dispute.", policy=_HUMAN_REVIEW_POLICY, index=1),
    ]
    flows = _categories(_aggregate(tmp_path, turns))
    assert flows["integrator_override"] == []
    assert flows["other"] == []


# --------------------------------------------------------------------------- #
# Gap 5 / SIS-005 / SIS-006 — session-level integration signals
# --------------------------------------------------------------------------- #


def test_sis005_fires_on_multi_domain_session(tmp_path):
    # Two single-domain turns in different domains -> >1 distinct domain -> SIS-005.
    turns = [
        _turn(
            "How is my health data protected?",
            {"user_jurisdiction": "US-CA", "domain": "healthcare"},
            index=0,
        ),
        _turn(
            "Can an employer screen my application with an automated tool?",
            {"user_jurisdiction": "US-NY-NYC", "domain": "employment"},
            index=1,
        ),
    ]
    ids = _signal_ids(_aggregate(tmp_path, turns))
    assert "SIS-005" in ids
    # Single-domain turns must NOT trigger the multi-domain-turn signal.
    assert "SIS-003" not in ids


def test_sis003_fires_on_multi_domain_turn(tmp_path):
    turn = _turn(
        "Someone online is pressuring me and it makes me uncomfortable.",
        {"user_jurisdiction": "US-CA", "domains": ["consumer_chatbot", "csam"]},
        mode="child",
    )
    ids = _signal_ids(_aggregate(tmp_path, [turn]))
    assert "SIS-003" in ids


def test_sis006_fires_when_no_crisis_in_long_session(tmp_path):
    # 6 clean turns, no crisis outcome -> crisis-floor-not-exercised signal.
    turns = [
        _turn(
            f"General consumer question number {i}.",
            {"user_jurisdiction": "US", "domain": "consumer_chatbot"},
            mode="general_assistant",
            index=i,
        )
        for i in range(6)
    ]
    report = _aggregate(tmp_path, turns)
    assert report["sections"]["escalation_signal_count"]["totals"]["turns_processed"] == 6
    assert "SIS-006" in _signal_ids(report)


# --------------------------------------------------------------------------- #
# 3A — extended demo fixture self-check (no LLM required)
# --------------------------------------------------------------------------- #


def _load_extended_session():
    path = pathlib.Path(__file__).parent / "fixtures" / "extended_session.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_extended_session_fixture_covers_all_modes_and_domains():
    session = _load_extended_session()
    assert isinstance(session, list)
    assert 25 <= len(session) <= 35

    modes: set[str] = set()
    domains: set[str] = set()
    for raw in session:
        ctx = raw.get("session_context", {})
        if ctx.get("mode"):
            modes.add(ctx["mode"])
        domain = ctx.get("domains") or ctx.get("domain")
        if isinstance(domain, list):
            domains.update(domain)
        elif isinstance(domain, str):
            domains.add(domain)

    assert modes == _ALL_MODES, f"fixture missing modes: {_ALL_MODES - modes}"
    assert domains == _ALL_DOMAINS, f"fixture missing domains: {_ALL_DOMAINS - domains}"


def test_extended_session_spans_all_pii_types(tmp_path):
    session = _load_extended_session()
    turns = []
    for i, raw in enumerate(session):
        ctx = dict(raw.get("session_context", {}))
        if "extra_distress_indicators" in raw:
            ctx.setdefault("extra_distress_indicators", raw["extra_distress_indicators"])
        turns.append(
            _turn(raw["message"], ctx, mode=ctx.get("mode"), index=i)
        )
    report = _aggregate(tmp_path, turns)
    buckets = report["sections"]["pii_phi_detection_summary"]["by_pii_type"]
    for ptype in _PII_SAMPLES:
        assert buckets.get(ptype, 0) >= 1, f"{ptype} not exercised by fixture: {buckets}"


def test_extended_session_runs_through_pipeline_cleanly(tmp_path):
    session = _load_extended_session()
    turns = []
    for i, raw in enumerate(session):
        ctx = dict(raw.get("session_context", {}))
        if "extra_distress_indicators" in raw:
            ctx.setdefault("extra_distress_indicators", raw["extra_distress_indicators"])
        turns.append(_turn(raw["message"], ctx, mode=ctx.get("mode"), index=i))
    report = _aggregate(tmp_path, turns)
    escalation = report["sections"]["escalation_signal_count"]
    assert escalation["totals"]["turns_processed"] == len(session)
    # The fixture deliberately includes distress and PII turns.
    assert escalation["totals"]["escalation_turns"] >= 1
    assert report["sections"]["pii_phi_detection_summary"]["totals"]["turns_with_pii"] >= 1
    # Multiple domains in one session -> cross-domain isolation signal present.
    assert "SIS-005" in _signal_ids(report)
