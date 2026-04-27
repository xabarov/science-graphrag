"""Early validation before Qdrant upsert (dim mismatch vs collection schema)."""

from __future__ import annotations

# pylint: disable=protected-access

from unittest.mock import MagicMock

import numpy as np
import pytest

from science_graphrag.ingestion.chunking import DocumentChunk
from science_graphrag.storage.qdrant_store.chunk_store import QdrantChunkStore
from science_graphrag.storage.qdrant_store.work_embeddings import QdrantWorkEmbeddingStore


def test_chunk_store_rejects_vector_batch_dim_mismatch() -> None:
    """upsert_chunks must not call Qdrant when vector width != store vector_dim."""
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._vector_dim = 384
    store._collection = "test-chunks"
    store._client = MagicMock()
    bad = np.zeros((1, 100), dtype=np.float32)
    with pytest.raises(ValueError, match="dim mismatch"):
        store.upsert_chunks(
            work_id="w",
            document_id="d",
            chunks=["x"],
            vectors=bad,
            embedding_model="hash",
        )
    store._client.upsert.assert_not_called()


def test_chunk_store_document_chunks_rejects_dim_mismatch() -> None:
    """upsert_document_chunks validates ndarray width against configured dim."""
    store = QdrantChunkStore.__new__(QdrantChunkStore)
    store._vector_dim = 384
    store._collection = "test-chunks"
    store._client = MagicMock()
    ch = DocumentChunk(
        chunk_fingerprint="a" * 64,
        section_path="## Abstract",
        text="hello",
        start_offset=0,
        end_offset=5,
        overlap_prev=False,
        overlap_next=False,
        chunk_index=0,
    )
    bad = np.zeros((1, 50), dtype=np.float32)
    with pytest.raises(ValueError, match="dim mismatch"):
        store.upsert_document_chunks(
            work_id="w",
            document_id="d",
            document_chunks=[ch],
            vectors=bad,
            embedding_model="hash",
        )
    store._client.upsert.assert_not_called()


def test_work_embedding_store_rejects_vector_dim_mismatch() -> None:
    """upsert_work_summary rejects wrong-length vectors before upsert."""
    store = QdrantWorkEmbeddingStore.__new__(QdrantWorkEmbeddingStore)
    store._vector_dim = 384
    store._collection = "test-work"
    store._client = MagicMock()
    with pytest.raises(ValueError, match="dim mismatch"):
        store.upsert_work_summary(
            work_id="w1",
            vector=[0.0] * 100,
            embedding_model="hash",
            workspace_ids=[],
        )
    store._client.upsert.assert_not_called()
