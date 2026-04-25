from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.agent.cypher_safety import CypherNotAllowedError
from science_graphrag.agent.tools import build_tool_registry


def _fake_stores() -> MagicMock:
    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    return stores


def test_build_tool_registry_returns_six_tools() -> None:
    tools = build_tool_registry(_fake_stores())
    assert len(tools) == 6
    tool_names = {tool.name for tool in tools}
    assert "cypher_query" in tool_names
    assert "idea_search" in tool_names


def test_cypher_query_tool_rejects_write() -> None:
    tools = build_tool_registry(_fake_stores())
    cypher_tool = next(tool for tool in tools if tool.name == "cypher_query")
    with pytest.raises(CypherNotAllowedError):
        cypher_tool.invoke({"query": "MATCH (n) DELETE n"})
