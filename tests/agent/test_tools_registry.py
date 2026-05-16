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


def test_build_tool_registry_includes_core_and_catalog_tools() -> None:
    tools = build_tool_registry(_fake_stores())
    tool_names = [getattr(t, "name", "") for t in tools]
    assert len(tool_names) == len(set(tool_names)), "registry must not register duplicate tools"
    uniq = set(tool_names)
    assert "cypher_query" in uniq
    assert "idea_search" in uniq
    assert "workspace_inspect" in uniq
    assert "workspace_graph_reltypes" in uniq
    assert "find_works" in uniq
    assert "format_bibliography_gost" in uniq
    assert "web_search" in uniq
    assert "web_fetch" in uniq
    assert "arxiv_search" in uniq
    assert "arxiv_fetch" in uniq
    assert "unpaywall_lookup" in uniq
    assert "openalex_works_search" in uniq
    assert "semantic_scholar_search" in uniq
    assert "semantic_scholar_paper" in uniq
    assert "read_external_pdf" in uniq


def test_build_retrieval_tools_includes_web_research() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools

    tools = build_retrieval_tools(_fake_stores())
    names = {getattr(t, "name", "") for t in tools}
    assert "web_search" in names
    assert "web_fetch" in names
    assert "arxiv_search" in names
    assert "arxiv_fetch" in names
    assert "unpaywall_lookup" in names
    assert "openalex_works_search" in names
    assert "semantic_scholar_search" in names
    assert "semantic_scholar_paper" in names
    assert "read_external_pdf" in names


def test_build_retrieval_tools_skips_openalex_when_disabled() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools
    from science_graphrag.config import Settings

    st = Settings(external_research_source_openalex_enabled=False)
    tools = build_retrieval_tools(_fake_stores(), settings=st)
    names = {getattr(t, "name", "") for t in tools}
    assert "openalex_works_search" not in names
    assert "web_search" in names


def test_build_retrieval_tools_skips_semantic_scholar_when_disabled() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools
    from science_graphrag.config import Settings

    st = Settings(external_research_source_semantic_scholar_enabled=False)
    tools = build_retrieval_tools(_fake_stores(), settings=st)
    names = {getattr(t, "name", "") for t in tools}
    assert "semantic_scholar_search" not in names
    assert "semantic_scholar_paper" not in names
    assert "web_search" in names


def test_build_retrieval_tools_skips_crossref_when_disabled() -> None:
    from science_graphrag.agent.tools import build_retrieval_tools
    from science_graphrag.config import Settings

    st = Settings(external_research_source_crossref_enabled=False)
    tools = build_retrieval_tools(_fake_stores(), settings=st)
    names = {getattr(t, "name", "") for t in tools}
    assert "web_search" not in names
    assert "web_fetch" not in names
    assert "arxiv_search" in names


def test_cypher_query_tool_rejects_write() -> None:
    tools = build_tool_registry(_fake_stores())
    cypher_tool = next(tool for tool in tools if tool.name == "cypher_query")
    with pytest.raises(CypherNotAllowedError):
        cypher_tool.invoke({"query": "MATCH (n) DELETE n"})
