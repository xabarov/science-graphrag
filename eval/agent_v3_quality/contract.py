"""Frozen identifiers and schema versions for agent v3 quality judge benchmark."""

from __future__ import annotations

# Top-level JSON artifact (implementation plan §6.1).
REVIEW_VERSION = "agent-v3-quality-judge-v1"
LOGICAL_FAMILY_ID = "agent_v3_quality_judge_v1"
BENCHMARK_FAMILY_SHORT = "agent_v3_quality_judge"

# Per-case gold.json (implementation plan §3.2).
CASE_SCHEMA_VERSION = "agent_v3_quality_case_v1"

CASE_FAMILIES: tuple[str, ...] = (
    "workspace_stats",
    "catalog_resolution",
    "quote_evidence",
    "dual_evidence_compare",
    "relation_tracing",
    "open_research",
)

TIER_JUDGE_MINI = "judge_mini"
TIER_JUDGE_PILOT = "judge_pilot"
TIER_JUDGE_HOLDOUT = "judge_holdout"

# Rubric axis weights (sum = 1.0) — spec §6.1 example.
RUBRIC_WEIGHTS: dict[str, float] = {
    "correctness": 0.30,
    "completeness": 0.20,
    "groundedness": 0.20,
    "synthesis_quality": 0.15,
    "usefulness": 0.10,
    "brevity_discipline": 0.05,
}

RUBRIC_AXES: tuple[str, ...] = tuple(RUBRIC_WEIGHTS.keys())
