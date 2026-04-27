"""Shared pool name → Settings attribute mapping for LLM concurrency (Phase 2 / Phase 5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings

# Span / policy pool_name -> Settings attribute holding max concurrent calls.
POOL_SETTING_ATTRS: dict[str, str] = {
    "references": "llm_concurrency_extraction_references",
    "claims": "llm_concurrency_claims",
    "semantic": "llm_concurrency_semantic",
    "dedup": "llm_concurrency_dedup",
    "metadata": "llm_concurrency_default",
    "ingestion": "llm_concurrency_default",
    "query_answer": "llm_concurrency_query_answer",
    "idea_assist": "llm_concurrency_summary",
    "agent_classifier": "llm_concurrency_agent_classifier",
    "agent_chat": "llm_concurrency_agent_chat",
    "vl_pdf": "llm_concurrency_default",
    "translation": "llm_concurrency_translation",
    "summary": "llm_concurrency_summary",
    "default": "llm_concurrency_default",
}


def pool_concurrency_limit(settings: "Settings", pool_name: str) -> int:
    """Effective slot count for ``pool_name`` (minimum 1)."""

    attr = POOL_SETTING_ATTRS.get(pool_name, "llm_concurrency_default")
    return max(1, int(getattr(settings, attr)))
