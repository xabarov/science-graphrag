"""Unit tests for ``idea_search`` tool."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from science_graphrag.agent.tools.idea_search import IdeaSearchTool
from science_graphrag.config import Settings


@pytest.fixture(name="settings")
def fixture_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "test-key-for-settings")
    return Settings()


def test_idea_search_empty_query_after_normalization(settings: Settings) -> None:
    chunk_store = MagicMock()
    work_store = MagicMock()
    tool = IdeaSearchTool(chunk_store, work_store=work_store, settings=settings)
    r = tool.run(q="   \n\t  ", kinds=["chunk"], workspace_id="ws-1", top_k=5)
    assert r.row_count == 0
    assert r.payload.get("empty_reason") == "empty_query"
    chunk_store.search_similar.assert_not_called()
