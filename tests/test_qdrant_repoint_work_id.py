"""Qdrant payload repoint after merge-work (Neo4j ↔ Qdrant consistency)."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.storage.qdrant_store import QdrantChunkStore


def test_repoint_work_id_payload_noop_when_same() -> None:
    store = QdrantChunkStore.__new__(QdrantChunkStore)  # bypass __init__ / collection create
    store._collection = "chunks"  # pylint: disable=protected-access
    store._client = MagicMock()  # pylint: disable=protected-access
    n = store.repoint_work_id_payload(from_work_id="a", to_work_id="a")
    assert n == 0
    store._client.count.assert_not_called()  # pylint: disable=protected-access


def test_repoint_work_id_payload_calls_set_payload() -> None:
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._collection = "chunks"  # pylint: disable=protected-access
    mock = MagicMock()
    mock.count.return_value.count = 3
    store._client = mock  # pylint: disable=protected-access
    n = store.repoint_work_id_payload(from_work_id="drop", to_work_id="keep")
    assert n == 3
    mock.set_payload.assert_called_once()
    call_kw = mock.set_payload.call_args.kwargs
    assert call_kw["payload"] == {"work_id": "keep"}
    assert call_kw["wait"] is True
