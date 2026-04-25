from __future__ import annotations

from typing import Any

import numpy as np
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.observability.spans import traced_tool_span
from science_graphrag.observability.spans.decorators import embeddings_span
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


class IdeaSearchTool(BaseAgentTool):
    name = "idea_search"

    def __init__(
        self,
        chunk_store: QdrantChunkStore,
        work_store: QdrantWorkEmbeddingStore | None = None,
        *,
        settings: Settings,
    ) -> None:
        self._chunk_store = chunk_store
        self._work_store = work_store
        self._embedder = resolve_embedder(settings)
        span_label = resolve_embedding_model_label(settings)
        if not settings.openrouter_embedding_model and not settings.embedding_model:
            span_label = "hash-deterministic"
        self._span_model_label = span_label

    def run(
        self,
        *,
        q: str,
        kinds: list[str] | None = None,
        workspace_id: str | None = None,
        top_k: int = 5,
    ) -> ToolResult:
        with traced_tool_span(
            "tool.idea_search",
            tool_name="idea_search",
            tool_parameters={"query": q[:200], "workspace_id": workspace_id or "", "top_k": top_k},
        ):
            k = max(1, min(int(top_k), 24))
            with embeddings_span(
                "embedding.agent.idea_search",
                attributes={"embedding.model_name": self._span_model_label},
            ):
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
            return ToolResult(
                payload={"items": items}, row_count=len(items), truncated=len(items) >= k
            )


class IdeaSearchArgs(BaseModel):
    query: str = Field(..., description="Natural-language search query.")
    kinds: list[str] = Field(
        default_factory=lambda: ["chunk"], description="Result kinds: chunk/work."
    )
    workspace_id: str | None = Field(default=None, description="Workspace scope.")
    top_k: int = Field(default=5, ge=1, le=24, description="Max items to return.")


def _make_idea_search_tool(
    chunk_store: QdrantChunkStore,
    work_store: QdrantWorkEmbeddingStore | None,
    *,
    settings: Settings,
) -> BaseTool:
    runtime_tool = IdeaSearchTool(chunk_store, work_store=work_store, settings=settings)

    @tool("idea_search", args_schema=IdeaSearchArgs, return_direct=False)
    def idea_search_tool(
        query: str,
        kinds: list[str] | None = None,
        workspace_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Search similar chunks and works using embedding retrieval."""
        result = runtime_tool.run(q=query, kinds=kinds, workspace_id=workspace_id, top_k=top_k)
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return idea_search_tool
