"""Chunk vectors in Qdrant (per-document sections)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
from qdrant_client import QdrantClient

from science_graphrag.storage.qdrant_store import chunk_store_read as _chunk_read
from science_graphrag.storage.qdrant_store import chunk_store_write as _chunk_write

if TYPE_CHECKING:
    from science_graphrag.ingestion.chunking import DocumentChunk


class QdrantChunkStore:
    def __init__(self, url: str, collection: str, vector_dim: int) -> None:
        self._client = QdrantClient(url=url, check_compatibility=False)
        self._collection = collection
        self._vector_dim = vector_dim
        _chunk_write.ensure_chunk_collection(self._client, self._collection, self._vector_dim)

    def upsert_chunks(
        self,
        *,
        work_id: str,
        document_id: str,
        chunks: list[str],
        vectors: np.ndarray,
        embedding_model: str,
    ) -> None:
        _chunk_write.upsert_chunks(
            self._client,
            self._collection,
            self._vector_dim,
            work_id=work_id,
            document_id=document_id,
            chunks=chunks,
            vectors=vectors,
            embedding_model=embedding_model,
        )

    def upsert_document_chunks(
        self,
        *,
        work_id: str,
        document_id: str,
        document_chunks: list[DocumentChunk],
        vectors: np.ndarray,
        embedding_model: str,
        workspace_ids: list[str] | None = None,
    ) -> None:
        _chunk_write.upsert_document_chunks(
            self._client,
            self._collection,
            self._vector_dim,
            work_id=work_id,
            document_id=document_id,
            document_chunks=document_chunks,
            vectors=vectors,
            embedding_model=embedding_model,
            workspace_ids=workspace_ids,
        )

    def repoint_work_id_payload(self, *, from_work_id: str, to_work_id: str) -> int:
        return _chunk_write.repoint_work_id_payload(
            self._client, self._collection, from_work_id=from_work_id, to_work_id=to_work_id
        )

    def add_workspace_to_chunks(self, *, work_id: str, workspace_id: str) -> int:
        return _chunk_write.add_workspace_to_chunks(
            self._client, self._collection, work_id=work_id, workspace_id=workspace_id
        )

    def remove_workspace_from_chunks(self, *, work_id: str, workspace_id: str) -> int:
        return _chunk_write.remove_workspace_from_chunks(
            self._client, self._collection, work_id=work_id, workspace_id=workspace_id
        )

    def add_workspace_to_all_chunks(
        self,
        *,
        workspace_id: str,
        progress_log_every: int = 2048,
    ) -> int:
        return _chunk_write.add_workspace_to_all_chunks(
            self._client,
            self._collection,
            workspace_id=workspace_id,
            progress_log_every=progress_log_every,
        )

    def delete_points_by_document_id(self, *, document_id: str) -> int:
        return _chunk_write.delete_points_by_document_id(
            self._client, self._collection, document_id=document_id
        )

    def delete_points_by_work_id(self, *, work_id: str) -> int:
        return _chunk_write.delete_points_by_work_id(
            self._client, self._collection, work_id=work_id
        )

    def scroll_points_payload_only(
        self,
        *,
        limit: int,
        offset: int | str | None = None,
    ) -> tuple[list[Any], int | str | None]:
        return _chunk_read.scroll_points_payload_only(
            self._client, self._collection, limit=limit, offset=offset
        )

    def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 8,
        work_id: str | None = None,
        work_ids: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return _chunk_read.search_similar_chunks(
            self._client,
            self._collection,
            vector=vector,
            limit=limit,
            work_id=work_id,
            work_ids=work_ids,
            workspace_id=workspace_id,
        )

    def count_chunks_for_work(self, *, work_id: str) -> int:
        return _chunk_read.count_chunks_for_work(self._client, self._collection, work_id=work_id)

    def count_chunks_for_workspace_work(self, *, workspace_id: str, work_id: str) -> int:
        return _chunk_read.count_chunks_for_workspace_work(
            self._client, self._collection, workspace_id=workspace_id, work_id=work_id
        )

    def scroll_chunks_for_work(
        self,
        *,
        work_id: str,
        limit: int = 50,
        offset: int | str | None = None,
    ) -> tuple[list[dict[str, Any]], int | str | None]:
        return _chunk_read.scroll_chunks_for_work(
            self._client, self._collection, work_id=work_id, limit=limit, offset=offset
        )

    def get_chunk_text_by_work_and_fingerprint(
        self,
        *,
        work_id: str,
        chunk_fingerprint: str,
    ) -> str | None:
        return _chunk_read.get_chunk_text_by_work_and_fingerprint(
            self._client,
            self._collection,
            work_id=work_id,
            chunk_fingerprint=chunk_fingerprint,
        )


def recreate_qdrant_chunk_collection(
    *,
    url: str,
    collection: str,
    vector_dim: int,
) -> QdrantChunkStore:
    """Drop collection if it exists, then return a store that creates a fresh empty collection."""

    client = QdrantClient(url=url, check_compatibility=False)
    names = {c.name for c in client.get_collections().collections}
    if collection in names:
        client.delete_collection(collection_name=collection)
    return QdrantChunkStore(url, collection, vector_dim)
