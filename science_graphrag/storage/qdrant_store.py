from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

if TYPE_CHECKING:
    from science_graphrag.ingestion.chunking import DocumentChunk

from science_graphrag.ingestion.chunking import infer_chunk_kind_from_section_path


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
                "workspace_ids": [],
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
        workspace_ids: list[str] | None = None,
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
            ws_ids = [str(x).strip() for x in (workspace_ids or []) if str(x).strip()]
            payload: dict[str, Any] = {
                "work_id": work_id,
                "document_id": document_id,
                "chunk_index": ch.chunk_index,
                "chunk_fingerprint": ch.chunk_fingerprint,
                "section_path": ch.section_path,
                "chunk_kind": infer_chunk_kind_from_section_path(ch.section_path),
                "language": "en",
                "overlap_prev": ch.overlap_prev,
                "overlap_next": ch.overlap_next,
                "start_offset": ch.start_offset,
                "end_offset": ch.end_offset,
                "text": ch.text[:8000],
                "embedding_model": embedding_model,
                "workspace_ids": ws_ids,
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

    def add_workspace_to_chunks(self, *, work_id: str, workspace_id: str) -> int:
        """Append ``workspace_id`` to payload.workspace_ids for all points of ``work_id`` (idempotent)."""

        wid = str(workspace_id or "").strip()
        if not wid:
            return 0
        flt = Filter(
            must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
        )
        updated = 0
        offset: int | str | None = None
        while True:
            records, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=flt,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not records:
                break
            for rec in records:
                payload = rec.payload or {}
                cur = [str(x).strip() for x in (payload.get("workspace_ids") or []) if str(x).strip()]
                if wid in cur:
                    continue
                cur.append(wid)
                self._client.set_payload(
                    collection_name=self._collection,
                    payload={"workspace_ids": cur},
                    points=[rec.id],
                    wait=True,
                )
                updated += 1
            if offset is None:
                break
        return updated

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
        work_ids: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return scored hits with payload (text, work_id, chunk metadata)."""

        query_filter = None
        ws_scope = (workspace_id or "").strip()
        must_clauses: list[Any] = []
        if ws_scope:
            must_clauses.append(
                FieldCondition(key="workspace_ids", match=MatchAny(any=[ws_scope])),
            )
        if work_id:
            must_clauses.append(FieldCondition(key="work_id", match=MatchValue(value=work_id)))
            query_filter = Filter(must=must_clauses) if must_clauses else None
        elif work_ids:
            cleaned = [str(w).strip() for w in work_ids if str(w).strip()]
            if cleaned:
                work_clause = Filter(
                    should=[FieldCondition(key="work_id", match=MatchValue(value=w)) for w in cleaned],
                )
                if must_clauses:
                    query_filter = Filter(must=[*must_clauses, work_clause])
                else:
                    query_filter = work_clause
        elif must_clauses:
            query_filter = Filter(must=must_clauses)
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
                    "chunk_kind": payload.get("chunk_kind"),
                    "language": payload.get("language"),
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


def _workspace_filter(workspace_id: str) -> Filter:
    wid = str(workspace_id or "").strip()
    return Filter(
        must=[
            FieldCondition(
                key="workspace_ids",
                match=MatchAny(any=[wid]),
            ),
        ],
    )


class QdrantWorkEmbeddingStore:
    """One embedding point per Work (title + abstract + first author summary) for Wave L dedup."""

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

    @staticmethod
    def point_id_for_work(work_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"work-embed:{work_id}"))

    def upsert_work_summary(
        self,
        *,
        work_id: str,
        vector: list[float] | np.ndarray,
        embedding_model: str,
        workspace_ids: list[str],
        title: str | None = None,
        publication_year: int | None = None,
        doi: str | None = None,
        arxiv_id: str | None = None,
        first_author_normalized: str | None = None,
        embedding_kind: str = "work_summary_v1",
    ) -> None:
        wid = str(work_id or "").strip()
        if not wid:
            return
        vec = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        ws_ids = [str(x).strip() for x in (workspace_ids or []) if str(x).strip()]
        pid = self.point_id_for_work(wid)
        payload: dict[str, Any] = {
            "work_id": wid,
            "embedding_model": embedding_model,
            "kind": embedding_kind,
            "embedding_kind": embedding_kind,
            "workspace_ids": ws_ids,
            "title": (title or "")[:2000],
            "year": publication_year,
            "doi": ((doi or "").strip())[:512],
            "arxiv_id": ((arxiv_id or "").strip())[:64],
            "first_author_normalized": (first_author_normalized or "")[:512],
        }
        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(id=pid, vector=vec, payload=payload),
            ],
            wait=True,
        )

    def add_workspace_to_work_point(self, *, work_id: str, workspace_id: str) -> bool:
        """Append workspace_id to payload.workspace_ids for the work summary point (idempotent)."""

        wid = str(workspace_id or "").strip()
        if not wid:
            return False
        pid = self.point_id_for_work(work_id)
        try:
            pts = self._client.retrieve(
                collection_name=self._collection,
                ids=[pid],
                with_payload=True,
                with_vectors=False,
            )
        except Exception:  # noqa: BLE001
            return False
        if not pts:
            return False
        payload = pts[0].payload or {}
        cur = [str(x).strip() for x in (payload.get("workspace_ids") or []) if str(x).strip()]
        if wid in cur:
            return False
        cur.append(wid)
        self._client.set_payload(
            collection_name=self._collection,
            payload={"workspace_ids": cur},
            points=[pid],
            wait=True,
        )
        return True

    def delete_by_work_id(self, *, work_id: str) -> int:
        pid = self.point_id_for_work(work_id)
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=[pid],
                wait=True,
            )
        except Exception:  # noqa: BLE001
            return 0
        return 1

    def retrieve_vector_for_work(self, *, work_id: str) -> list[float] | None:
        pid = self.point_id_for_work(work_id)
        try:
            pts = self._client.retrieve(
                collection_name=self._collection,
                ids=[pid],
                with_payload=False,
                with_vectors=True,
            )
        except Exception:  # noqa: BLE001
            return None
        if not pts:
            return None
        raw = pts[0].vector
        if raw is None:
            return None
        if isinstance(raw, dict):
            vals = next(iter(raw.values()), None)
            if vals is None:
                return None
            return [float(x) for x in vals]
        return [float(x) for x in raw]

    def repoint_work_id_payload(self, *, from_work_id: str, to_work_id: str) -> int:
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
            ).count,
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

    def search_similar_works(
        self,
        *,
        vector: list[float],
        workspace_id: str,
        limit: int,
        exclude_work_id: str | None = None,
    ) -> list[dict[str, Any]]:
        flt = _workspace_filter(workspace_id)
        ex = (exclude_work_id or "").strip()
        if ex:
            flt = Filter(
                must=flt.must,
                must_not=[FieldCondition(key="work_id", match=MatchValue(value=ex))],
            )
        resp = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            query_filter=flt,
            with_payload=True,
        )
        out: list[dict[str, Any]] = []
        for hit in resp.points:
            payload = hit.payload or {}
            owid = str(payload.get("work_id") or "")
            if ex and owid == ex:
                continue
            out.append(
                {
                    "work_id": owid,
                    "score": float(hit.score),
                    "embedding_model": payload.get("embedding_model"),
                },
            )
        return out

    def list_work_ids_in_workspace(self, *, workspace_id: str) -> list[str]:
        """Return distinct work_ids that have a summary point tagged with this workspace."""

        wid = str(workspace_id or "").strip()
        if not wid:
            return []
        seen: set[str] = set()
        out: list[str] = []
        offset: int | str | None = None
        flt = _workspace_filter(wid)
        while True:
            records, offset = self._client.scroll(
                collection_name=self._collection,
                scroll_filter=flt,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not records:
                break
            for rec in records:
                payload = rec.payload or {}
                w = str(payload.get("work_id") or "").strip()
                if w and w not in seen:
                    seen.add(w)
                    out.append(w)
            if offset is None:
                break
        return out


class QdrantAuthorEmbeddingStore:
    """One embedding per Author for workspace-scoped author dedup (L2)."""

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

    @staticmethod
    def point_id_for_author(author_id: str) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"author-embed:{author_id}"))

    def upsert_author_summary(
        self,
        *,
        author_id: str,
        vector: list[float] | np.ndarray,
        embedding_model: str,
        workspace_ids: list[str],
    ) -> None:
        aid = str(author_id or "").strip()
        if not aid:
            return
        vec = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        ws_ids = [str(x).strip() for x in (workspace_ids or []) if str(x).strip()]
        pid = self.point_id_for_author(aid)
        payload: dict[str, Any] = {
            "author_id": aid,
            "embedding_model": embedding_model,
            "kind": "author_summary",
            "workspace_ids": ws_ids,
        }
        self._client.upsert(
            collection_name=self._collection,
            points=[PointStruct(id=pid, vector=vec, payload=payload)],
            wait=True,
        )

    def search_similar_authors(
        self,
        *,
        vector: list[float],
        workspace_id: str,
        limit: int,
        exclude_author_id: str | None = None,
    ) -> list[dict[str, Any]]:
        flt = _workspace_filter(workspace_id)
        ex = (exclude_author_id or "").strip()
        if ex:
            flt = Filter(
                must=flt.must,
                must_not=[FieldCondition(key="author_id", match=MatchValue(value=ex))],
            )
        resp = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=limit,
            query_filter=flt,
            with_payload=True,
        )
        out: list[dict[str, Any]] = []
        for hit in resp.points:
            payload = hit.payload or {}
            aid = str(payload.get("author_id") or "")
            if ex and aid == ex:
                continue
            out.append({"author_id": aid, "score": float(hit.score)})
        return out

    def delete_by_author_id(self, *, author_id: str) -> int:
        pid = self.point_id_for_author(author_id)
        try:
            self._client.delete(
                collection_name=self._collection,
                points_selector=[pid],
                wait=True,
            )
        except Exception:  # noqa: BLE001
            return 0
        return 1

    def retrieve_vector_for_author(self, *, author_id: str) -> list[float] | None:
        pid = self.point_id_for_author(author_id)
        try:
            pts = self._client.retrieve(
                collection_name=self._collection,
                ids=[pid],
                with_payload=False,
                with_vectors=True,
            )
        except Exception:  # noqa: BLE001
            return None
        if not pts:
            return None
        raw = pts[0].vector
        if raw is None:
            return None
        if isinstance(raw, dict):
            vals = next(iter(raw.values()), None)
            if vals is None:
                return None
            return [float(x) for x in vals]
        return [float(x) for x in raw]
