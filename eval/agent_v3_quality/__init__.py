"""Advisory pairwise LLM-judge benchmark: ``langgraph_research_v1`` vs ``langgraph_supervisor_v3``.

Logical family id: ``agent_v3_quality_judge_v1``. See ``contract`` module and
``docs/analysis/agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md``.
"""

from eval.agent_v3_quality.contract import (
    BENCHMARK_FAMILY_SHORT,
    CASE_SCHEMA_VERSION,
    LOGICAL_FAMILY_ID,
    REVIEW_VERSION,
)

__all__ = [
    "BENCHMARK_FAMILY_SHORT",
    "CASE_SCHEMA_VERSION",
    "LOGICAL_FAMILY_ID",
    "REVIEW_VERSION",
]
