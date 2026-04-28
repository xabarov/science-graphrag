"""Unit tests for ``paper_quote_search`` tool."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.agent.tools.paper_quote_search_tool import PaperQuoteSearchTool
from science_graphrag.config import Settings


@pytest.fixture(name="settings")
def fixture_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "test-key-for-settings")
    return Settings()


def test_paper_quote_search_empty_reason_no_hits(settings: Settings) -> None:
    store = MagicMock()
    store.search_similar.return_value = []
    tool = PaperQuoteSearchTool(store, settings=settings)
    r = tool.run(query="anchors", workspace_id="ws-1", top_k=5)
    assert r.row_count == 0
    assert r.payload.get("empty_reason") == "no_hits_workspace_scoped"


def test_paper_quote_search_empty_reason_no_hits_for_work(settings: Settings) -> None:
    store = MagicMock()
    store.search_similar.return_value = []
    tool = PaperQuoteSearchTool(store, settings=settings)
    r = tool.run(query="anchors", workspace_id="ws-1", work_id="work-99", top_k=5)
    assert r.row_count == 0
    assert r.payload.get("empty_reason") == "no_hits_for_work"


def test_paper_quote_search_empty_reason_no_hits_corpus_wide(settings: Settings) -> None:
    store = MagicMock()
    store.search_similar.return_value = []
    tool = PaperQuoteSearchTool(store, settings=settings)
    r = tool.run(query="anchors", workspace_id=None, work_id=None, top_k=5)
    assert r.payload.get("empty_reason") == "no_hits_corpus_wide"


def test_paper_quote_search_empty_reason_empty_query(settings: Settings) -> None:
    store = MagicMock()
    tool = PaperQuoteSearchTool(store, settings=settings)
    r = tool.run(query="   ", workspace_id="ws-1")
    assert r.payload.get("empty_reason") == "empty_query"
    store.search_similar.assert_not_called()
