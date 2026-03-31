from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

if TYPE_CHECKING:
    from science_graphrag.ingestion.chunking import DocumentChunk


class QdrantChunkStore:
    def __init__(self, url: str, collection: str, vector_dim: int) -> None:
        self._client = QdrantClient(url=url, check_compatibility=False)
        self._collection = collection
        self._vector_dim = vector_dim
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        cols = self._client.get_collections().collections
        names = {c.name for c in cols}
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=self._vector_dim, distance=Distance.COSINE),
            )

    def upsert_chunks(
        self,
        *,
        work_id: str,
        document_id: str,
        chunks: list[str],
        vectors: np.ndarray,
        embedding_model: str,
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        points: list[PointStruct] = []
        for idx, (text, vec) in enumerate(zip(chunks, vectors, strict=True)):
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{idx}"))
            payload: dict[str, Any] = {
                "work_id": work_id,
                "document_id": document_id,
                "chunk_index": idx,
                "text": text[:8000],
                "embedding_model": embedding_model,
            }
            points.append(
                PointStruct(
                    id=pid,
                    vector=vec.tolist(),
                    payload=payload,
                )
            )
        if points:
            self._client.upsert(collection_name=self._collection, points=points)

    def upsert_document_chunks(
        self,
        *,
        work_id: str,
        document_id: str,
        document_chunks: list[DocumentChunk],
        vectors: np.ndarray,
        embedding_model: str,
    ) -> None:
        """Upsert section-aware chunks with deterministic ids from chunk_fingerprint."""
        if len(document_chunks) != len(vectors):
            raise ValueError("document_chunks and vectors length mismatch")
        points: list[PointStruct] = []
        for ch, vec in zip(document_chunks, vectors, strict=True):
            pid = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{document_id}:{ch.chunk_fingerprint}",
                ),
            )
            payload: dict[str, Any] = {
                "work_id": work_id,
                "document_id": document_id,
                "chunk_index": ch.chunk_index,
                "chunk_fingerprint": ch.chunk_fingerprint,
                "section_path": ch.section_path,
                "overlap_prev": ch.overlap_prev,
                "overlap_next": ch.overlap_next,
                "start_offset": ch.start_offset,
                "end_offset": ch.end_offset,
                "text": ch.text[:8000],
                "embedding_model": embedding_model,
            }
            points.append(
                PointStruct(
                    id=pid,
                    vector=vec.tolist(),
                    payload=payload,
                ),
            )
        if points:
            self._client.upsert(collection_name=self._collection, points=points)

    def search_similar(
        self,
        *,
        vector: list[float],
        limit: int = 8,
        work_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return scored hits with payload (text, work_id, chunk metadata)."""

        query_filter = None
        if work_id:
            query_filter = Filter(
                must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
            )
        # qdrant-client>=1.17: use query_points (search() removed)
        resp = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        hits = resp.points
        out: list[dict[str, Any]] = []
        for hit in hits:
            payload = hit.payload or {}
            out.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "text": payload.get("text"),
                    "work_id": payload.get("work_id"),
                    "document_id": payload.get("document_id"),
                    "chunk_fingerprint": payload.get("chunk_fingerprint"),
                    "section_path": payload.get("section_path"),
                },
            )
        return out
