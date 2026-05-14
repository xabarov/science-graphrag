"""Retrieval answer orchestration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal

from science_graphrag.stores.registry import StoreRegistry
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.retrieval.llm_answer import _try_query_answer_llm
from science_graphrag.retrieval.neo4j_context import (
    _graph_context_for_hits,
    _workspace_scope_work_ids,
)
from science_graphrag.retrieval.qdrant_search import (
    _hybrid_hits_for_answer,
    _qdrant_hits_for_answer,
)
from science_graphrag.retrieval.query_embedder import embed_query
from science_graphrag.retrieval.ranking import _citations_and_snippets_from_hits
from science_graphrag.retrieval.trace_payload import _retrieval_trace_payload, _RetrievalTraceIn
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore

logger = logging.getLogger(__name__)


@dataclass
class GroundedAnswer:
    """Retrieval result for POST /v1/query."""

    answer: str
    citations: list[dict[str, Any]]
    graph_context: dict[str, Any]
    retrieval_trace: dict[str, Any]


def answer_query(
    question: str,
    *,
    settings: Settings | None = None,
    stores: StoreRegistry | None = None,
    work_id: str | None = None,
    workspace_id: str | None = None,
    top_k: int = 5,
    mode: Literal["vector", "hybrid"] = "vector",
    retrieval_mode: str | None = None,
) -> GroundedAnswer:
    """Return grounded answer from retrieval core."""
    s = settings or get_settings()
    owned_neo4j: Neo4jGraphStore | None = None
    if stores is None:
        owned_neo4j = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
        owned_qdrant = QdrantChunkStore(
            s.qdrant_url,
            s.qdrant_collection,
            vector_dim=resolve_embedding_dim(settings=s),
        )
        neo4j = owned_neo4j
        qdrant_chunks = owned_qdrant
    else:
        neo4j = stores.neo4j
        qdrant_chunks = stores.qdrant_chunks

    raw_mode = retrieval_mode if retrieval_mode is not None else mode
    mode_norm: Literal["vector", "hybrid"] = (
        "hybrid" if (raw_mode or "").strip().lower() == "hybrid" else "vector"
    )
    ws_meta: dict[str, Any] = {}
    ws_scope_payload_miss: str | None = None
    work_ids_filter: list[str] | None = None
    wid_param = (work_id or "").strip() or None
    ws_param = (workspace_id or "").strip() or None
    if ws_param and not wid_param:
        work_ids_filter, ws_meta = _workspace_scope_work_ids(neo4j, ws_param)

    if work_ids_filter is not None and len(work_ids_filter) == 0:
        _, emb_trace = embed_query(question, s)
        hits = []
        emb_trace = {**emb_trace, **ws_meta}
    else:
        q_work_ids = (
            None
            if wid_param
            else (work_ids_filter if work_ids_filter and len(work_ids_filter) > 0 else None)
        )
        ws_qdrant = ws_param if (ws_param and not wid_param) else None
        if mode_norm == "hybrid":
            _, emb_trace, hits = _hybrid_hits_for_answer(
                question=question,
                settings=s,
                neo4j=neo4j,
                qdrant_chunks=qdrant_chunks,
                work_id=wid_param,
                work_ids=None if ws_qdrant else q_work_ids,
                top_k=top_k,
                workspace_id=ws_qdrant,
            )
        else:
            _, emb_trace, hits = _qdrant_hits_for_answer(
                question=question,
                settings=s,
                qdrant_chunks=qdrant_chunks,
                work_id=wid_param,
                work_ids=None if ws_qdrant else q_work_ids,
                top_k=top_k,
                workspace_id=ws_qdrant,
            )
        if ws_meta:
            emb_trace = {**emb_trace, **ws_meta}
        if ws_qdrant and not hits and q_work_ids and len(q_work_ids) > 0:
            _, emb_trace_fb, hits = (
                _hybrid_hits_for_answer(
                    question=question,
                    settings=s,
                    neo4j=neo4j,
                    qdrant_chunks=qdrant_chunks,
                    work_id=None,
                    work_ids=q_work_ids,
                    top_k=top_k,
                    workspace_id=None,
                )
                if mode_norm == "hybrid"
                else _qdrant_hits_for_answer(
                    question=question,
                    settings=s,
                    qdrant_chunks=qdrant_chunks,
                    work_id=None,
                    work_ids=q_work_ids,
                    top_k=top_k,
                    workspace_id=None,
                )
            )
            logger.warning(
                "workspace_scope_payload_miss: no Qdrant hits with workspace_ids filter for "
                "workspace_id=%s; retrying with work_id list (%d works). Backfill workspace_ids on chunks "
                "if this persists.",
                ws_qdrant,
                len(q_work_ids),
            )
            ws_scope_payload_miss = "work_ids_payload"
            emb_trace = {**emb_trace_fb, **ws_meta}

    citations, snippets = _citations_and_snippets_from_hits(hits)
    graph, resolved_work = _graph_context_for_hits(neo4j, wid_param, hits)

    if snippets:
        joined = " ".join(snippets[:3])
        answer = (
            "Retrieved context (not LLM-paraphrased): "
            + joined[:1200]
            + ("…" if len(joined) > 1200 else "")
        )
    else:
        answer = "No retrieved chunks; ingest documents or check Qdrant collection."

    synthesis: dict[str, Any] = {"mode": "deterministic_snippets", "second_stage_llm": False}
    extra_degraded: list[str] = []
    llm_answer, llm_meta = _try_query_answer_llm(question, citations, s)
    if llm_answer:
        answer = llm_answer
        synthesis = {
            "mode": "grounded_llm_paraphrase",
            "second_stage_llm": True,
            "model": llm_meta.get("model"),
        }
    elif llm_meta.get("error"):
        extra_degraded.append("second_stage_llm_failed")
        synthesis = {
            "mode": "deterministic_snippets",
            "second_stage_llm": False,
            "second_stage_error": llm_meta.get("error"),
        }
    elif llm_meta.get("skipped"):
        synthesis = {
            "mode": "deterministic_snippets",
            "second_stage_llm": False,
            "second_stage_skipped": llm_meta.get("reason") or True,
        }

    retrieval_policy = (
        "hybrid_rrf_v1;neo4j_fulltext_works;graph_cites_expand;qdrant_multi_lane"
        if mode_norm == "hybrid"
        else None
    )
    trace_payload = _retrieval_trace_payload(
        _RetrievalTraceIn(
            emb_trace,
            hits,
            wid_param,
            resolved_work,
            s.qdrant_collection,
            top_k,
            len(citations),
        ),
        query_preview=question,
        answer_synthesis=synthesis,
        extra_degraded=extra_degraded,
        workspace_id=ws_param,
        retrieval_mode=mode_norm,
        retrieval_policy=retrieval_policy,
    )
    if ws_meta:
        trace_payload = {**trace_payload, **ws_meta}
    if ws_scope_payload_miss:
        trace_payload = {**trace_payload, "workspace_scope_payload_miss": ws_scope_payload_miss}

    try:
        return GroundedAnswer(
            answer=answer,
            citations=citations,
            graph_context=graph,
            retrieval_trace=trace_payload,
        )
    finally:
        if owned_neo4j is not None:
            owned_neo4j.close()
