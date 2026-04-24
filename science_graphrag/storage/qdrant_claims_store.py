"""Qdrant collection for claim text vectors (Wave O)."""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from science_graphrag.ingestion.claims.models import ClaimDraft
from science_graphrag.ingestion.embeddings import EmbeddingProvider


class QdrantClaimsStore:
    """Separate collection from chunks; deterministic point ids per claim_id."""

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

    def delete_points_by_work_id(self, *, work_id: str) -> int:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        flt = Filter(must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))])
        res = self._client.count(collection_name=self._collection, count_filter=flt, exact=True)
        n = int(res.count)
        if n == 0:
            return 0
        self._client.delete(collection_name=self._collection, points_selector=flt, wait=True)
        return n

    def upsert_claims(
        self,
        *,
        work_id: str,
        claims: list[ClaimDraft],
        embedder: EmbeddingProvider,
        embedding_model: str,
    ) -> None:
        if not claims:
            return
        texts = [c.normalized_text for c in claims]
        vectors = embedder.embed(texts)
        if len(vectors) != len(claims):
            raise ValueError("claims embedding length mismatch")
        points: list[PointStruct] = []
        for claim, vec in zip(claims, vectors, strict=True):
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"claim_point:{claim.claim_id}"))
            ev_ids = [e.evidence_id for e in claim.evidence]
            payload: dict[str, Any] = {
                "claim_id": claim.claim_id,
                "work_id": work_id,
                "normalized_text": claim.normalized_text[:4000],
                "polarity": claim.polarity,
                "claim_type": claim.claim_type,
                "supporting_evidence_ids": ev_ids,
                "topics": [],
                "embedding_model": embedding_model,
                "embedding_kind": "claim_normalized_v1",
            }
            points.append(PointStruct(id=pid, vector=vec.tolist(), payload=payload))
        self._client.upsert(collection_name=self._collection, points=points)
