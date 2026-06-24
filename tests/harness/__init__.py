"""4-axis compliance test harness for saski-shadow.

Axis 1 (axis1_matching)  - law matching golden tables (deterministic).
Axis 2 (axis2_detection) - text -> PII + distress detection.
Axis 3 (axis3_pipeline)  - full analyze_turn -> persist -> aggregate.
Axis 4 (axis4_live)      - LLM-in-the-loop, marked ``live`` and skipped in CI.

Axes 1-3 are collected and run by pytest normally (see the ``python_files``
pattern in pyproject.toml, which includes ``axis*.py``).
"""
