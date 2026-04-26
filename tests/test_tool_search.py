"""Tests for rule-based tool shortlist (Wave A CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.tools import tool

from science_graphrag.agent.tool_search import (
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
    tools = [_named_tool("idea_search"), _named_tool("workspace_overview")]
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
