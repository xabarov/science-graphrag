"""Semantic chunk quote search for agent tools (CH2)."""

from __future__ import annotations

from typing import Any

import numpy as np
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.chunk_retrieval_defaults import (
    AGENT_CHUNK_QUOTE_TEXT_MAX_CHARS,
    AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE,
    DEFAULT_AGENT_CHUNK_TOP_K,
    MAX_AGENT_CHUNK_TOP_K,
    normalize_agent_retrieval_query,
)
from science_graphrag.config import Settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.observability.spans import SpanAttributes, set_span_error
from science_graphrag.observability.spans.decorators import embeddings_span, retriever_span
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
        top_k: int = DEFAULT_AGENT_CHUNK_TOP_K,
    ) -> ToolResult:
        q = normalize_agent_retrieval_query(query or "")
        if not q:
            return ToolResult(
                payload={
                    "items": [],
                    "quote_candidates": [],
                    "row_count": 0,
                    "empty_reason": "empty_query",
                },
                row_count=0,
            )
        k = max(1, min(int(top_k), MAX_AGENT_CHUNK_TOP_K))
        dim = resolve_embedding_dim(settings=self._settings)
        ws = (workspace_id or "").strip() or None
        wid = (work_id or "").strip() or None

        with embeddings_span("embedding.agent.paper_quote_search"):
            SpanAttributes.set_embedding_agent_attrs(
                self._span_model_label,
                dim=dim,
                input_count=1,
            )
            qv = self._embedder.embed([q])
        if isinstance(qv, np.ndarray):
            vector = qv[0].tolist()
        else:
            vector = list(qv[0])

        with retriever_span("retrieval.qdrant.paper_quote_search"):
            SpanAttributes.set_retrieval_qdrant_context(
                collection_name=self._settings.qdrant_collection,
                top_k=k,
                workspace_id=ws,
                work_id=wid,
                query_preview=q,
            )
            try:
                hits = list(
                    self._chunk_store.search_similar(
                        vector=vector,
                        limit=k,
                        workspace_id=ws,
                        work_id=wid,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                set_span_error(exc)
                return ToolResult(
                    payload={
                        "error": "qdrant_unavailable",
                        "items": [],
                        "quote_candidates": [],
                        "row_count": 0,
                        "empty_reason": "qdrant_unavailable",
                    },
                    row_count=0,
                )

            doc_rows: list[dict[str, Any]] = []
            for h in hits:
                text = str(h.get("text") or "")
                w = str(h.get("work_id") or "")
                fp = str(h.get("chunk_fingerprint") or h.get("id") or "")
                doc_rows.append(
                    {
                        "id": fp or h.get("id"),
                        "score": h.get("score"),
                        "snippet": text[:AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE],
                        "work_id": w,
                        "chunk_fingerprint": fp,
                    }
                )
            SpanAttributes.set_retrieval_documents(doc_rows)

        if not hits:
            if (wid or "").strip():
                empty_reason = "no_hits_for_work"
            elif (ws or "").strip():
                empty_reason = "no_hits_workspace_scoped"
            else:
                empty_reason = "no_hits_corpus_wide"
            return ToolResult(
                payload={
                    "items": [],
                    "quote_candidates": [],
                    "row_count": 0,
                    "empty_reason": empty_reason,
                },
                row_count=0,
            )

        items: list[dict[str, Any]] = []
        quote_candidates: list[dict[str, Any]] = []
        for h in hits:
            text = str(h.get("text") or "")
            w = str(h.get("work_id") or "")
            fp = str(h.get("chunk_fingerprint") or h.get("id") or "")
            sec = str(h.get("section_path") or "")
            items.append(
                {
                    "chunk_fingerprint": fp,
                    "work_id": w,
                    "score": h.get("score"),
                    "snippet": text[:AGENT_CHUNK_SNIPPET_CHARS_PAPER_QUOTE],
                    "section_path": sec,
                }
            )
            quote_candidates.append(
                {
                    "quote_text": text[:AGENT_CHUNK_QUOTE_TEXT_MAX_CHARS],
                    "work_id": w,
                    "chunk_id": fp,
                    **({"chunk_fingerprint": fp} if fp else {}),
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
    query: str = Field(
        ...,
        min_length=1,
        description=(
            "Natural-language query for the passage to locate; keep focused. Query text is "
            "normalized the same way as idea_search (trim + collapse whitespace) before "
            "embedding. After a short idea_search, reuse wording from returned chunk snippets "
            "when possible."
        ),
    )
    workspace_id: str | None = Field(
        default=None,
        description=(
            "When the user cares about this workspace only, pass the same workspace_id as in the "
            "user message (scopes Qdrant chunk filters)."
        ),
    )
    work_id: str | None = Field(
        default=None,
        description=(
            "Internal Work id from find_works, paper_profile, or graph tools—restricts retrieval "
            "to that paper's chunks when already known."
        ),
    )
    top_k: int = Field(
        default=DEFAULT_AGENT_CHUNK_TOP_K,
        ge=1,
        le=MAX_AGENT_CHUNK_TOP_K,
        description="Max chunk hits (aligned with idea_search chunk retrieval).",
    )
