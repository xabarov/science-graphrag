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

    def repoint_work_id_payload(self, *, from_work_id: str, to_work_id: str) -> int:
        """
        Set payload.work_id from ``from_work_id`` to ``to_work_id`` for all matching points.

        Required after ``merge_work_into_canonical`` so retrieval citations match Neo4j :Work ids.
        """

        if from_work_id == to_work_id:
            return 0
        flt = Filter(
            must=[FieldCondition(key="work_id", match=MatchValue(value=from_work_id))],
        )
        n_before = int(
            self._client.count(
                collection_name=self._collection,
                count_filter=flt,
                exact=True,
            ).count
        )
        if n_before == 0:
            return 0
        self._client.set_payload(
            collection_name=self._collection,
            payload={"work_id": to_work_id},
            points=flt,
            wait=True,
        )
        return n_before

    def delete_points_by_document_id(self, *, document_id: str) -> int:
        """Remove all points whose payload ``document_id`` matches (re-ingest / cleanup)."""

        flt = Filter(
            must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))],
        )
        res = self._client.count(
            collection_name=self._collection,
            count_filter=flt,
            exact=True,
        )
        n = int(res.count)
        if n == 0:
            return 0
        self._client.delete(
            collection_name=self._collection,
            points_selector=flt,
            wait=True,
        )
        return n

    def delete_points_by_work_id(self, *, work_id: str) -> int:
        """Remove all points for a Work (purge / repair). Use with care on shared corpora."""

        flt = Filter(
            must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
        )
        res = self._client.count(
            collection_name=self._collection,
            count_filter=flt,
            exact=True,
        )
        n = int(res.count)
        if n == 0:
            return 0
        self._client.delete(
            collection_name=self._collection,
            points_selector=flt,
            wait=True,
        )
        return n

    def scroll_points_payload_only(
        self,
        *,
        limit: int,
        offset: int | str | None = None,
    ) -> tuple[list[Any], int | str | None]:
        """Low-level scroll for diagnostics (payload only, no vectors)."""

        return self._client.scroll(
            collection_name=self._collection,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

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
            fp = payload.get("chunk_fingerprint")
            if not fp:
                # Legacy upserts (`upsert_chunks`) omitted fingerprints; use stable point id for
                # citations, benchmarks, and UI keys until chunks are re-ingested with fingerprints.
                fp = str(hit.id)
            out.append(
                {
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "text": payload.get("text"),
                    "work_id": payload.get("work_id"),
                    "document_id": payload.get("document_id"),
                    "chunk_fingerprint": fp,
                    "section_path": payload.get("section_path"),
                },
            )
        return out

    def count_chunks_for_work(self, *, work_id: str) -> int:
        """Approximate count of points for a work (for pagination total)."""

        flt = Filter(
            must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
        )
        res = self._client.count(
            collection_name=self._collection,
            count_filter=flt,
            exact=True,
        )
        return int(res.count)

    def scroll_chunks_for_work(
        self,
        *,
        work_id: str,
        limit: int = 50,
        offset: int | str | None = None,
    ) -> tuple[list[dict[str, Any]], int | str | None]:
        """List chunk payloads for one work (ordered by scroll order)."""

        flt = Filter(
            must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
        )
        records, next_offset = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=flt,
            limit=limit,
            offset=offset,
            with_payload=True,
        )
        out: list[dict[str, Any]] = []
        for rec in records:
            payload = rec.payload or {}
            out.append(
                {
                    "document_id": payload.get("document_id"),
                    "chunk_fingerprint": payload.get("chunk_fingerprint"),
                    "section_path": payload.get("section_path"),
                    "text": payload.get("text"),
                    "chunk_index": payload.get("chunk_index"),
                },
            )
        return out, next_offset


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
