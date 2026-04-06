"""Qdrant delete by document_id / work_id."""

from __future__ import annotations

from unittest.mock import MagicMock

from science_graphrag.storage.qdrant_store import QdrantChunkStore


def test_delete_points_by_document_id_noop_when_zero() -> None:
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._collection = "chunks"  # pylint: disable=protected-access
    mock = MagicMock()
    mock.count.return_value.count = 0
    store._client = mock  # pylint: disable=protected-access
    n = store.delete_points_by_document_id(document_id="doc-1")
    assert n == 0
    mock.delete.assert_not_called()


def test_delete_points_by_document_id_calls_delete() -> None:
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._collection = "chunks"  # pylint: disable=protected-access
    mock = MagicMock()
    mock.count.return_value.count = 2
    store._client = mock  # pylint: disable=protected-access
    n = store.delete_points_by_document_id(document_id="doc-1")
    assert n == 2
    mock.delete.assert_called_once()


def test_delete_points_by_work_id_calls_delete() -> None:
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._collection = "chunks"  # pylint: disable=protected-access
    mock = MagicMock()
    mock.count.return_value.count = 5
    store._client = mock  # pylint: disable=protected-access
    n = store.delete_points_by_work_id(work_id="w-1")
    assert n == 5
    mock.delete.assert_called_once()
