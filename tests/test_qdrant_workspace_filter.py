"""Qdrant workspace scope filter uses MatchAny on array payload ``workspace_ids``."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from qdrant_client.models import FieldCondition, MatchAny

from science_graphrag.storage.qdrant_store import QdrantChunkStore


def test_search_similar_workspace_filter_uses_matchany() -> None:
    store = object.__new__(QdrantChunkStore)
    store._collection = "test-coll"
    store._vector_dim = 4
    mock_client = MagicMock()
    mock_client.query_points.return_value = MagicMock(points=[])
    store._client = mock_client

    store.search_similar(vector=[0.1, 0.2, 0.3, 0.4], limit=2, workspace_id="ws-xyz")

    kwargs: dict[str, Any] = mock_client.query_points.call_args.kwargs
    flt = kwargs["query_filter"]
    assert flt is not None
    assert len(flt.must) >= 1
    fc0 = flt.must[0]
    assert isinstance(fc0, FieldCondition)
    assert fc0.key == "workspace_ids"
    assert isinstance(fc0.match, MatchAny)
    assert fc0.match.any == ["ws-xyz"]
