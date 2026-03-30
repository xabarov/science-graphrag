from __future__ import annotations

import uuid
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


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
