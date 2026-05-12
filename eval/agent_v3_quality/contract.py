"""Frozen identifiers and schema versions for agent v3 quality judge benchmark."""

from __future__ import annotations

import os

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
    "quote_evidence_grounding",
    "dual_evidence_compare",
    "relation_tracing",
    "open_research",
    "negative_case_refusal",
    "multi_workspace_inspect",
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

# Must match ``judge_prompt_fingerprint()`` for ``eval/agent_v3_quality/judge_prompt_v1.md``.
# Bump when the judge prompt file changes (starts a new stabilization window).
EXPECTED_JUDGE_PROMPT_FINGERPRINT = "sha256-20:5b68007c9ae3d6801673"

# OpenRouter-style defaults for ``--judge-model-family`` (override via env per family).
_JUDGE_FAMILY_ENV: dict[str, str] = {
    "deepseek": "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_JUDGE_MODEL_DEEPSEEK",
    "anthropic": "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_JUDGE_MODEL_ANTHROPIC",
    "openai": "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_JUDGE_MODEL_OPENAI",
}
_JUDGE_FAMILY_DEFAULT_MODEL: dict[str, str] = {
    "deepseek": "deepseek/deepseek-chat",
    "anthropic": "anthropic/claude-haiku-4.5",
    "openai": "openai/gpt-4o-mini",
}

JUDGE_MODEL_FAMILY_IDS: frozenset[str] = frozenset(_JUDGE_FAMILY_DEFAULT_MODEL.keys())


def resolve_benchmark_judge_model(
    *,
    judge_model: str | None,
    judge_model_family: str | None,
) -> str | None:
    """Resolve explicit ``--judge-model`` or ``--judge-model-family`` to a model id."""

    explicit = (judge_model or "").strip()
    if explicit:
        return explicit
    fam_raw = (judge_model_family or "").strip().lower()
    if not fam_raw:
        return None
    env_name = _JUDGE_FAMILY_ENV.get(fam_raw)
    if env_name:
        from_env = (os.environ.get(env_name) or "").strip()
        if from_env:
            return from_env
    default = _JUDGE_FAMILY_DEFAULT_MODEL.get(fam_raw)
    return (default or "").strip() or None
