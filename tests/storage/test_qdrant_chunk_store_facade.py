"""Tests for ``QdrantChunkStore`` facade delegation to read/write split modules."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import science_graphrag.storage.qdrant_store.chunk_store as chunk_store_mod
import science_graphrag.storage.qdrant_store.chunk_store_write as chunk_store_write


@pytest.fixture(name="chunk_store")
def _chunk_store() -> object:
    with patch.object(chunk_store_mod, "QdrantClient", return_value=MagicMock()):
        with patch.object(chunk_store_mod._chunk_write, "ensure_chunk_collection"):
            store = chunk_store_mod.QdrantChunkStore("http://qdrant", "chunks", vector_dim=4)
    return store


def test_facade_repoint_delegates_to_write_module(chunk_store: object) -> None:
    with patch.object(
        chunk_store_mod._chunk_write, "repoint_work_id_payload", return_value=3
    ) as rep:
        n = chunk_store.repoint_work_id_payload(from_work_id="a", to_work_id="b")  # type: ignore[union-attr]
    assert n == 3
    kwargs = rep.call_args.kwargs
    assert kwargs["from_work_id"] == "a"
    assert kwargs["to_work_id"] == "b"


def test_facade_delete_points_by_work_id_delegates(chunk_store: object) -> None:
    with patch.object(
        chunk_store_mod._chunk_write, "delete_points_by_work_id", return_value=5
    ) as fn:
        n = chunk_store.delete_points_by_work_id(work_id="w99")  # type: ignore[union-attr]
    assert n == 5
    fn.assert_called_once()


def test_upsert_chunks_builds_points_and_calls_client() -> None:
    client = MagicMock()
    chunks = ["hello", "world"]
    vectors = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    chunk_store_write.upsert_chunks(
        client,
        "col",
        3,
        work_id="w1",
        document_id="doc-1",
        chunks=chunks,
        vectors=vectors,
        embedding_model="m",
    )
    client.upsert.assert_called_once()
    points = client.upsert.call_args.kwargs["points"]
    assert len(points) == 2
    assert points[0].payload["chunk_index"] == 0
    assert points[1].payload["workspace_ids"] == []
