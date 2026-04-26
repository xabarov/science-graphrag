"""Semantic chunk quote search for agent tools (CH2)."""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.observability.spans import traced_tool_span
from science_graphrag.observability.spans.decorators import embeddings_span
from science_graphrag.storage.qdrant_store import QdrantChunkStore


class PaperQuoteSearchTool(BaseAgentTool):
    name = "paper_quote_search"

    def __init__(self, chunk_store: QdrantChunkStore, *, settings: Settings) -> None:
        self._chunk_store = chunk_store
        self._embedder = resolve_embedder(settings)
        self._settings = settings
        span_label = resolve_embedding_model_label(settings)
        if not settings.openrouter_embedding_model and not settings.embedding_model:
            span_label = "hash-deterministic"
        self._span_model_label = span_label

    def run(
        self,
        *,
        query: str,
        workspace_id: str | None,
        work_id: str | None = None,
        top_k: int = 5,
    ) -> ToolResult:
        q = (query or "").strip()
        if not q:
            return ToolResult(
                payload={"items": [], "quote_candidates": [], "row_count": 0},
                row_count=0,
            )
        k = max(1, min(int(top_k), 16))
        try:
            with traced_tool_span(
                "tool.paper_quote_search",
                tool_name="paper_quote_search",
                tool_parameters={
                    "query": q[:200],
                    "workspace_id": workspace_id or "",
                    "work_id": work_id or "",
                },
            ):
                with embeddings_span(
                    "embedding.agent.paper_quote_search",
                    attributes={"embedding.model_name": self._span_model_label},
                ):
                    qv = self._embedder.embed([q])
                if isinstance(qv, np.ndarray):
                    vector = qv[0].tolist()
                else:
                    vector = list(qv[0])
                hits = self._chunk_store.search_similar(
                    vector=vector,
                    limit=k,
                    workspace_id=(workspace_id or "").strip() or None,
                    work_id=(work_id or "").strip() or None,
                )
        except Exception:  # noqa: BLE001
            return ToolResult(
                payload={
                    "error": "qdrant_unavailable",
                    "items": [],
                    "quote_candidates": [],
                    "row_count": 0,
                },
                row_count=0,
            )
        items: list[dict[str, Any]] = []
        quote_candidates: list[dict[str, Any]] = []
        for h in hits:
            text = str(h.get("text") or "")
            wid = str(h.get("work_id") or "")
            fp = str(h.get("chunk_fingerprint") or h.get("id") or "")
            sec = str(h.get("section_path") or "")
            items.append(
                {
                    "chunk_fingerprint": fp,
                    "work_id": wid,
                    "score": h.get("score"),
                    "snippet": text[:400],
                    "section_path": sec,
                }
            )
            quote_candidates.append(
                {
                    "quote_text": text[:800],
                    "work_id": wid,
                    "chunk_id": fp,
                    "section": sec or None,
                }
            )
        return ToolResult(
            payload={
                "items": items,
                "quote_candidates": quote_candidates,
                "row_count": len(items),
            },
            row_count=len(items),
        )


class PaperQuoteArgs(BaseModel):
    query: str = Field(..., min_length=1)
    workspace_id: str | None = None
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=16)
