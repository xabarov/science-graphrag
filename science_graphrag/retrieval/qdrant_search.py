"""Qdrant/Neo4j retrieval lanes for answer generation."""

from __future__ import annotations

import re
from typing import Any

from science_graphrag.config import Settings
from science_graphrag.retrieval.query_embedder import embed_query
from science_graphrag.retrieval.ranking import _rank_hits_for_answer, _reciprocal_rank_fusion
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _qdrant_hits_for_answer(
    *,
    question: str,
    settings: Settings,
    qdrant_chunks: QdrantChunkStore,
    work_id: str | None,
    work_ids: list[str] | None,
    top_k: int,
    workspace_id: str | None = None,
) -> tuple[list[float], dict[str, Any], list[dict[str, Any]]]:
    vec, emb_trace = embed_query(question, settings)
    fetch_limit = min(max(top_k * 8, top_k), 48)
    hits_raw = qdrant_chunks.search_similar(
        vector=vec,
        limit=fetch_limit,
        work_id=work_id,
        work_ids=work_ids,
        workspace_id=workspace_id,
    )
    return vec, emb_trace, _rank_hits_for_answer(hits_raw, top_k=top_k)


def _sanitize_fulltext_query(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    sanitized = re.sub(r"[^a-zA-Z0-9\s\-.]", " ", raw)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized[:220] if sanitized else raw[:220]


def _hybrid_hits_for_answer(
    *,
    question: str,
    settings: Settings,
    neo4j: Neo4jGraphStore,
    qdrant_chunks: QdrantChunkStore,
    work_id: str | None,
    work_ids: list[str] | None,
    top_k: int,
    workspace_id: str | None = None,
) -> tuple[list[float], dict[str, Any], list[dict[str, Any]]]:
    oversample = max(top_k * 6, 24)
    vec, emb_trace, hits_vector = _qdrant_hits_for_answer(
        question=question,
        settings=settings,
        qdrant_chunks=qdrant_chunks,
        work_id=work_id,
        work_ids=work_ids,
        top_k=oversample,
        workspace_id=workspace_id,
    )
    fulltext_query = _sanitize_fulltext_query(question)
    fulltext_works: list[tuple[str, float]] = []
    graph_works: list[str] = []
    if fulltext_query:
        fulltext_works = neo4j.fulltext_search_work_ids(fulltext_query, limit=20)

    seeds: list[str] = []
    for hit in hits_vector[:10]:
        wid = hit.get("work_id")
        if wid:
            seeds.append(str(wid))
    for wid, _score in fulltext_works[:12]:
        seeds.append(wid)
    seeds = list(dict.fromkeys(seeds))

    exclude_ids: set[str] = set()
    if work_id:
        exclude_ids.add(str(work_id).strip())
    graph_works = neo4j.cites_neighbor_work_ids(seeds, exclude_ids=exclude_ids, limit=60)

    lanes: list[list[dict[str, Any]]] = [hits_vector]
    fulltext_ids = [wid for wid, _score in fulltext_works][:18]
    if fulltext_ids:
        raw_ft = qdrant_chunks.search_similar(
            vector=vec,
            limit=36,
            work_id=None,
            work_ids=fulltext_ids,
            workspace_id=workspace_id,
        )
        lanes.append(_rank_hits_for_answer(raw_ft, top_k=max(top_k * 4, 16)))

    fulltext_set = set(fulltext_ids)
    graph_ids = [wid for wid in graph_works if wid not in fulltext_set][:18]
    if graph_ids:
        raw_graph = qdrant_chunks.search_similar(
            vector=vec,
            limit=28,
            work_id=None,
            work_ids=graph_ids,
            workspace_id=workspace_id,
        )
        lanes.append(_rank_hits_for_answer(raw_graph, top_k=max(top_k * 3, 12)))

    fused = _reciprocal_rank_fusion(lanes, k=60, top_n=top_k)
    emb_out = {
        **emb_trace,
        "hybrid": {
            "fulltext_work_hits": len(fulltext_works),
            "graph_extra_works": len(graph_works),
            "fusion_lanes": len(lanes),
            "fulltext_query": fulltext_query or None,
        },
    }
    return vec, emb_out, fused
