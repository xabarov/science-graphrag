"""Tests for rule-based tool shortlist (Wave A CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.tools import tool

from science_graphrag.agent.tool_search import (
    shortlist_tools_for_single_agent,
    shortlist_tools_for_specialist,
    strip_tool_search_context_wrappers,
)
from science_graphrag.config import Settings


def _named_tool(name: str):
    @tool(name)
    def _t(x: str = "") -> dict:
        """Test stub tool."""
        return {"row_count": 0}

    return _t


def test_strip_tool_search_context_wrappers_removes_active_workspace_id() -> None:
    raw = "<active_workspace_id>\nws-uuid-1\n</active_workspace_id>\nсколько статей"
    assert strip_tool_search_context_wrappers(raw).strip() == "сколько статей"


def test_strip_tool_search_context_wrappers_removes_memory_blocks() -> None:
    raw = (
        "<session_memory>\nQ: old\nA: ans\n</session_memory>\n"
        "<client_history_digest>\n[]\n</client_history_digest>\n"
        "Собери список литературы по ГОСТ"
    )
    assert strip_tool_search_context_wrappers(raw).strip() == "Собери список литературы по ГОСТ"


def test_shortlist_bibliography_boosts_gost_with_memory_prefix() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_retrieval_tools(stores, settings)
    wrapped = (
        "<session_memory>\nnoise\n</session_memory>\n"
        "<client_history_digest>\n[]\n</client_history_digest>\n"
        "Собери список литературы по ГОСТ"
    )
    out, meta = shortlist_tools_for_specialist(
        tools,
        question=wrapped,
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
    )
    assert meta.get("reason") == "rules"
    names = {getattr(t, "name", "") for t in out}
    assert "format_bibliography_gost" in names


def test_shortlist_disabled_returns_full() -> None:
    tools = [_named_tool("idea_search"), _named_tool("workspace_inspect")]
    settings = Settings(agent_rule_tool_search_enabled=False)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="hello world",
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
    )
    assert len(out) == len(tools)
    assert meta.get("skipped") is True


def test_shortlist_bibliography_boosts_gost_tool() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_retrieval_tools(stores, settings)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="Собери список литературы по ГОСТ",
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
    )
    assert meta.get("reason") == "rules"
    names = {getattr(t, "name", "") for t in out}
    assert "format_bibliography_gost" in names


def test_writer_shortlist_is_skipped_minimal() -> None:
    tools = [_named_tool("final_answer")]
    settings = Settings(agent_rule_tool_search_enabled=True)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="Synthesize the answer with citations",
        specialist="writer_agent",
        settings=settings,
        has_workspace=True,
    )
    assert len(out) == 1
    assert meta.get("reason") == "writer_minimal_set"
    assert meta.get("skipped") is True


def test_graph_agent_shortlist_includes_cypher_for_graph_question() -> None:
    from science_graphrag.agent.tools import build_graph_tools

    stores = MagicMock()
    tools = build_graph_tools(stores)
    settings = Settings(agent_rule_tool_search_enabled=True)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="cypher neo4j path between entity A and B in the graph",
        specialist="graph_agent",
        settings=settings,
        has_workspace=True,
    )
    names = {getattr(t, "name", "") for t in out}
    assert "cypher_query" in names
    assert meta.get("reason") in ("rules", "fallback_full")


def test_retrieval_shortlist_always_includes_core_catalog_when_rules() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_retrieval_tools(stores, settings)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="how many papers in this workspace",
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
        answer_class="inventory",
    )
    assert meta.get("reason") == "rules"
    names = {getattr(t, "name", "") for t in out}
    for core in ("workspace_inspect", "paper_profile", "find_works"):
        assert core in names, f"missing {core}"


def test_retrieval_low_signal_returns_full() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_retrieval_tools(stores, settings)
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="a",
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
    )
    # Very short / low-signal questions fall back to full tool set
    assert meta.get("reason") in ("low_signal", "fallback_full") or len(out) == len(tools)


def test_shortlist_tools_for_single_agent_includes_final_answer() -> None:
    from science_graphrag.agent.tools import build_tool_registry

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_tool_registry(stores)
    out, meta = shortlist_tools_for_single_agent(
        tools,
        question="Show cypher graph cites path between works",
        settings=settings,
        has_workspace=True,
        answer_class="relation_tracing",
    )
    names = [getattr(t, "name", "") for t in out]
    assert "final_answer" in names
    assert meta.get("reason") == "rules"
    assert len(out) <= len(tools)
    assert len(out) < len(tools)


def test_shortlist_tools_for_single_agent_includes_paper_quote_search_for_evidence_tradeoff() -> (
    None
):
    """Heavy-suite style question should keep chunk-quote tool in the shortlist."""
    from science_graphrag.agent.tools import build_tool_registry

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=True)
    tools = build_tool_registry(stores)
    question = (
        "What trade-offs between speed and accuracy for real-time object detection does this "
        "workspace support with evidence? Use at least two distinct retrieval paths among "
        "idea_search, paper_quote_search, and workspace_inspect (blurb or papers). "
        "Cite at least two different work_ids from tool outputs. Finish with final_answer."
    )
    out, meta = shortlist_tools_for_single_agent(
        tools,
        question=question,
        settings=settings,
        has_workspace=True,
        answer_class=None,
    )
    names = {getattr(t, "name", "") for t in out}
    assert "paper_quote_search" in names, meta
    assert meta.get("reason") == "rules"


def test_shortlist_rules_meta_includes_score_band_from_settings() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    tools = build_retrieval_tools(stores, Settings(agent_rule_tool_search_enabled=True))
    settings = Settings(
        agent_rule_tool_search_enabled=True,
        agent_tool_search_score_band=2.5,
    )
    out, meta = shortlist_tools_for_specialist(
        tools,
        question="how many papers in this workspace",
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=True,
        answer_class="inventory",
    )
    assert meta.get("reason") == "rules"
    assert meta.get("score_band") == 2.5
    assert len(out) >= 3


def test_shortlist_tools_for_single_agent_disabled_returns_full() -> None:
    from science_graphrag.agent.tools import build_tool_registry

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    settings = Settings(agent_rule_tool_search_enabled=False)
    tools = build_tool_registry(stores)
    out, meta = shortlist_tools_for_single_agent(
        tools,
        question="anything",
        settings=settings,
        has_workspace=True,
    )
    assert len(out) == len(tools)
    assert meta.get("skipped") is True
