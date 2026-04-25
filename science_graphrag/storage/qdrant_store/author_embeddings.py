"""Author-level summary embeddings in Qdrant."""

from __future__ import annotations

import uuid
from typing import Any

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

from science_graphrag.storage.qdrant_store.filters import workspace_filter


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
        flt = workspace_filter(workspace_id)
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
