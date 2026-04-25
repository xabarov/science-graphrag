from __future__ import annotations

from typing import Any

import numpy as np

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


class IdeaSearchTool(BaseAgentTool):
    name = "idea_search"

    def __init__(
        self,
        chunk_store: QdrantChunkStore,
        work_store: QdrantWorkEmbeddingStore | None = None,
        *,
        embedding_model: str | None = None,
    ) -> None:
        self._chunk_store = chunk_store
        self._work_store = work_store
        self._embedding_model = embedding_model
        self._embedder = self._build_embedder(embedding_model)

    @staticmethod
    def _build_embedder(model_name: str | None):
        if model_name:
            maybe = try_sentence_transformer(model_name)
            if maybe is not None:
                return maybe
        return HashEmbeddingProvider()

    def run(
        self,
        *,
        q: str,
        kinds: list[str] | None = None,
        workspace_id: str | None = None,
        top_k: int = 5,
    ) -> ToolResult:
        k = max(1, min(int(top_k), 24))
        qv = self._embedder.embed([q])
        if isinstance(qv, np.ndarray):
            vector = qv[0].tolist()
        else:
            vector = list(qv[0])
        req_kinds = {str(x).strip().lower() for x in (kinds or ["chunk"])}
        items: list[dict[str, Any]] = []
        if "chunk" in req_kinds:
            for hit in self._chunk_store.search_similar(
                vector=vector, limit=k, workspace_id=workspace_id
            ):
                items.append(
                    {
                        "kind": "chunk",
                        "id": hit.get("id"),
                        "score": hit.get("score"),
                        "work_id": hit.get("work_id"),
                        "snippet": str(hit.get("text") or "")[:240],
                    }
                )
        if "work" in req_kinds and self._work_store is not None and workspace_id:
            for hit in self._work_store.search_similar_works(
                vector=vector, workspace_id=workspace_id, limit=k
            ):
                items.append(
                    {
                        "kind": "work",
                        "id": hit.get("work_id"),
                        "score": hit.get("score"),
                        "work_id": hit.get("work_id"),
                        "snippet": "",
                    }
                )
        items = sorted(items, key=lambda x: float(x.get("score") or 0.0), reverse=True)[:k]
        return ToolResult(payload={"items": items}, row_count=len(items), truncated=len(items) >= k)
