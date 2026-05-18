"""Feature-flagged external-fast routing (single retrieval hop, no corpus fan-out)."""

from __future__ import annotations

from science_graphrag.agent.coordination.question_features import QuestionFeatures

# Corpus / workspace tools blocked on the retrieval leg when fast path is active.
EXTERNAL_FAST_PATH_TOOL_DENYLIST: frozenset[str] = frozenset(
    {
        "find_works",
        "paper_profile",
        "idea_search",
        "paper_quote_search",
        "workspace_inspect",
        "spawn_subagent",
        "research_plan",
        "corpus_explore",
    }
)


def pure_external_web_fast_path_intent(features: QuestionFeatures) -> bool:
    """True when the turn is external web/scholar/PDF only (no corpus/graph compare)."""

    if not features.asks_for_web_research:
        return False
    if features.asks_for_relations or features.asks_for_compare:
        return False
    if features.asks_for_dual_evidence or features.asks_for_catalog_resolution:
        return False
    if features.asks_for_workspace_stats:
        return False
    if features.asks_for_anchor_free_quote or features.asks_for_quotes:
        return False
    return True


__all__ = [
    "EXTERNAL_FAST_PATH_TOOL_DENYLIST",
    "pure_external_web_fast_path_intent",
]
