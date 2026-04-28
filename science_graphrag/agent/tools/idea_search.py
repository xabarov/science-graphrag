from __future__ import annotations

from typing import Any

import numpy as np
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.chunk_retrieval_defaults import (
    DEFAULT_AGENT_CHUNK_TOP_K,
    MAX_AGENT_CHUNK_TOP_K,
    normalize_agent_retrieval_query,
)
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.observability.spans import SpanAttributes, set_span_attribute, set_span_error
from science_graphrag.observability.spans.decorators import embeddings_span, retriever_span
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
        self._settings = settings
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
        top_k: int = DEFAULT_AGENT_CHUNK_TOP_K,
    ) -> ToolResult:
        k = max(1, min(int(top_k), MAX_AGENT_CHUNK_TOP_K))
        qn = normalize_agent_retrieval_query(q)
        if not qn:
            return ToolResult(
                payload={"items": [], "row_count": 0, "empty_reason": "empty_query"},
                row_count=0,
            )
        req_kinds = {str(x).strip().lower() for x in (kinds or ["chunk"])}
        dim = resolve_embedding_dim(settings=self._settings)

        with embeddings_span("embedding.agent.idea_search"):
            SpanAttributes.set_embedding_agent_attrs(
                self._span_model_label,
                dim=dim,
                input_count=1,
            )
            qv = self._embedder.embed([qn])
        if isinstance(qv, np.ndarray):
            vector = qv[0].tolist()
        else:
            vector = list(qv[0])

        items: list[dict[str, Any]] = []
        retrieval_docs: list[dict[str, Any]] = []

        with retriever_span("retrieval.qdrant.idea_search"):
            SpanAttributes.set_retrieval_qdrant_context(
                collection_name=self._settings.qdrant_collection,
                top_k=k,
                workspace_id=workspace_id or None,
                query_preview=qn,
            )
            try:
                if "chunk" in req_kinds:
                    for hit in self._chunk_store.search_similar(
                        vector=vector, limit=k, workspace_id=workspace_id
                    ):
                        snippet = str(hit.get("text") or "")[:240]
                        wid = hit.get("work_id")
                        items.append(
                            {
                                "kind": "chunk",
                                "id": hit.get("id"),
                                "score": hit.get("score"),
                                "work_id": wid,
                                "snippet": snippet,
                            }
                        )
                        retrieval_docs.append(
                            {
                                "id": hit.get("id"),
                                "score": hit.get("score"),
                                "snippet": snippet,
                                "work_id": wid,
                                "kind": "chunk",
                            }
                        )
                if "work" in req_kinds and self._work_store is not None and workspace_id:
                    set_span_attribute(
                        "db.collection.works",
                        self._settings.qdrant_work_embeddings_collection,
                    )
                    for hit in self._work_store.search_similar_works(
                        vector=vector, workspace_id=workspace_id, limit=k
                    ):
                        wid = hit.get("work_id")
                        items.append(
                            {
                                "kind": "work",
                                "id": wid,
                                "score": hit.get("score"),
                                "work_id": wid,
                                "snippet": "",
                            }
                        )
                        retrieval_docs.append(
                            {
                                "id": wid,
                                "score": hit.get("score"),
                                "snippet": "",
                                "work_id": wid,
                                "kind": "work",
                            }
                        )
            except Exception as exc:  # noqa: BLE001
                set_span_error(exc)
                raise

            SpanAttributes.set_retrieval_documents(retrieval_docs)

        items = sorted(items, key=lambda x: float(x.get("score") or 0.0), reverse=True)[:k]
        return ToolResult(payload={"items": items}, row_count=len(items), truncated=len(items) >= k)


class IdeaSearchArgs(BaseModel):
    query: str = Field(
        ...,
        description=(
            "Natural-language search query; trimmed and internal whitespace collapsed "
            "(same normalization as paper_quote_search) before embedding."
        ),
    )
    kinds: list[str] = Field(
        default_factory=lambda: ["chunk"], description="Result kinds: chunk/work."
    )
    workspace_id: str | None = Field(default=None, description="Workspace scope.")
    top_k: int = Field(
        default=DEFAULT_AGENT_CHUNK_TOP_K,
        ge=1,
        le=MAX_AGENT_CHUNK_TOP_K,
        description="Max items to return.",
    )


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
        top_k: int = DEFAULT_AGENT_CHUNK_TOP_K,
    ) -> dict[str, Any]:
        """Embedding retrieval over chunks and/or work-level vectors (see kinds).

        Pass workspace_id when the user cares about this workspace only; omit for corpus-wide
        semantic exploration. Use chunk-heavy kinds for broad scan; include work when comparing papers.
        """
        result = run_tool_result_with_span(
            tool_name="idea_search",
            tool_parameters={
                "query": query[:200],
                "workspace_id": workspace_id or "",
                "top_k": top_k,
            },
            fn=lambda: runtime_tool.run(
                q=query, kinds=kinds, workspace_id=workspace_id, top_k=top_k
            ),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return idea_search_tool
