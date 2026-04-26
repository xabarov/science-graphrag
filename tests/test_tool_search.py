"""Tests for rule-based tool shortlist (Wave A CH3)."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.tools import tool

from science_graphrag.agent.tool_search import shortlist_tools_for_specialist
from science_graphrag.config import Settings


def _named_tool(name: str):
    @tool(name)
    def _t(x: str = "") -> dict:
        """Test stub tool."""
        return {"row_count": 0}

    return _t


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
