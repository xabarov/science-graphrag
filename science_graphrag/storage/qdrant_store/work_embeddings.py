"""Work-level summary embeddings in Qdrant."""

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

    def remove_workspace_from_work_point(self, *, work_id: str, workspace_id: str) -> bool:
        """Remove workspace_id from payload.workspace_ids on the work summary point (idempotent)."""

        ws = str(workspace_id or "").strip()
        if not ws:
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
        if ws not in cur:
            return False
        nxt = [x for x in cur if x != ws]
        self._client.set_payload(
            collection_name=self._collection,
            payload={"workspace_ids": nxt},
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
        flt = workspace_filter(workspace_id)
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
        flt = workspace_filter(wid)
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
