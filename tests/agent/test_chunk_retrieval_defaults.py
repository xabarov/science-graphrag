"""Tests for shared chunk retrieval defaults (agent tools)."""

from __future__ import annotations

from science_graphrag.agent.tools.chunk_retrieval_defaults import normalize_agent_retrieval_query


def test_normalize_agent_retrieval_query_collapses_whitespace() -> None:
    assert normalize_agent_retrieval_query("  a \n\t b  ") == "a b"


def test_normalize_agent_retrieval_query_empty() -> None:
    assert normalize_agent_retrieval_query("") == ""
    assert normalize_agent_retrieval_query("   ") == ""
