"""Vector retrieval + Neo4j graph context for query-time (Phase 5 MVP)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple

logger = logging.getLogger(__name__)

from openai import OpenAI

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import (
    HashEmbeddingProvider,
    resolve_embedding_dim,
    try_sentence_transformer,
)
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


@dataclass
class GroundedAnswer:
    """Retrieval result for POST /v1/query (deterministic snippets + optional second-stage LLM)."""

    answer: str
    citations: list[dict[str, Any]]
    graph_context: dict[str, Any]
    retrieval_trace: dict[str, Any]


def _embed_query(text: str, settings: Settings) -> tuple[list[float], dict[str, Any]]:
    embedder = HashEmbeddingProvider()
    model_label: str | None = None
    if settings.embedding_model:
        st = try_sentence_transformer(settings.embedding_model)
        if st is not None:
            embedder = st
            model_label = settings.embedding_model
    vec = embedder.embed([text])[0]
    trace = {
        "embedding_model": model_label or "hash-deterministic",
        "vector_dim": embedder.dim,
    }
    return vec.tolist(), trace


_SEMANTIC_EXISTS = (
    "(EXISTS { MATCH (w)-[:USES_METHOD]->(:Method) }) OR "
    "(EXISTS { MATCH (w)-[:EVALUATED_ON]->(:Dataset) })"
)


def _neo4j_graph_context_for_work(store: Neo4jGraphStore, work_id: str) -> dict[str, Any]:
    """
    Neo4j semantic neighborhood for query-time graph_context.

    Returns stable keys for UI: semantic_available, optional error, operational degraded[].
    """

    methods: list[str] = []
    datasets: list[str] = []
    try:
        with store.session() as session:
            row = session.run(
                f"""
                MATCH (w:Work {{id: $wid}})
                RETURN w.id AS wid,
                       {_SEMANTIC_EXISTS} AS semantic_available
                """,
                wid=work_id,
            ).single()
            if not row:
                return {
                    "methods": [],
                    "datasets": [],
                    "semantic_available": False,
                    "context_work_id": work_id,
                    "degraded": ["work_not_in_graph"],
                    "error": None,
                }
            semantic_available = bool(row["semantic_available"])
            for rec in session.run(
                """
                MATCH (:Work {id: $wid})-[:USES_METHOD]->(m:Method)
                RETURN DISTINCT coalesce(m.name, '') AS name
                """,
                wid=work_id,
            ):
                name = (rec["name"] or "").strip()
                if name:
                    methods.append(name)
            for rec in session.run(
                """
                MATCH (:Work {id: $wid})-[:EVALUATED_ON]->(d:Dataset)
                RETURN DISTINCT coalesce(d.name, '') AS name
                """,
                wid=work_id,
            ):
                name = (rec["name"] or "").strip()
                if name:
                    datasets.append(name)
            return {
                "methods": sorted(set(methods)),
                "datasets": sorted(set(datasets)),
                "semantic_available": semantic_available,
                "context_work_id": work_id,
                "degraded": [],
                "error": None,
            }
    except Exception:  # noqa: BLE001
        return {
            "methods": [],
            "datasets": [],
            "semantic_available": False,
            "context_work_id": work_id,
            "degraded": ["neo4j_unavailable"],
            "error": "neo4j_unavailable",
        }


# Section paths from PDF chunking often label tail sections; pure vector search still
# scores them highly when the question overlaps generic keywords ("object detection").
_BACK_MATTER_MARKERS: tuple[str, ...] = (
    "acknowledg",
    "reference",
    "references",
    "bibliograph",
    "appendix",
)


def _is_likely_back_matter_section(section_path: str | None) -> bool:
    if not section_path:
        return False
    s = section_path.lower()
    return any(m in s for m in _BACK_MATTER_MARKERS)


def _body_section_bonus(section_path: str | None) -> float:
    """Small score bump for intro/method-style headings (tie-break on cosine similarity)."""

    if not section_path:
        return 0.0
    s = section_path.lower()
    tiers: tuple[tuple[tuple[str, ...], float], ...] = (
        (("abstract", "summary"), 0.04),
        (("introduction", "intro", "overview"), 0.035),
        (("method", "approach", "architecture", "model", "network"), 0.03),
        (("experiment", "result", "evaluation", "implementation"), 0.02),
    )
    for keys, bonus in tiers:
        if any(k in s for k in keys):
            return bonus
    if "related work" in s:
        return 0.015
    return 0.0


def _rank_hits_for_answer(hits: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    """Deprioritize back-matter; among the rest, prefer abstract/intro/method-like sections."""

    if not hits:
        return []

    def sort_key(h: dict[str, Any]) -> tuple[bool, float]:
        sp = h.get("section_path")
        back_first = _is_likely_back_matter_section(sp)
        base = float(h.get("score") or 0.0)
        boosted = base + _body_section_bonus(sp)
        return (back_first, -boosted)

    ranked = sorted(hits, key=sort_key)
    return ranked[:top_k]


def _citations_and_snippets_from_hits(
    hits: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Build ranked citations and short snippets for the deterministic answer string."""

    citations: list[dict[str, Any]] = []
    snippets: list[str] = []
    for rank, h in enumerate(hits, start=1):
        text = (h.get("text") or "").strip()
        if not text:
            continue
        cit: dict[str, Any] = {
            "rank": rank,
            "score": h.get("score"),
            "work_id": h.get("work_id"),
            "document_id": h.get("document_id"),
            "chunk_fingerprint": h.get("chunk_fingerprint"),
            "section_path": h.get("section_path"),
            "excerpt": text[:600],
        }
        if h.get("chunk_kind") is not None:
            cit["chunk_kind"] = h.get("chunk_kind")
        if h.get("language") is not None:
            cit["language"] = h.get("language")
        if h.get("rrf_score") is not None:
            cit["rrf_score"] = h.get("rrf_score")
        citations.append(cit)
        snippets.append(text[:400])
    return citations, snippets


def _effective_work_id(work_id: str | None, hits: list[dict[str, Any]]) -> str | None:
    return work_id or (hits[0].get("work_id") if hits else None)


class _GraphAndResolved(NamedTuple):
    graph_context: dict[str, Any]
    resolved_work_id: str | None


def _graph_context_for_hits(
    neo4j: Neo4jGraphStore,
    work_id: str | None,
    hits: list[dict[str, Any]],
) -> _GraphAndResolved:
    effective = _effective_work_id(work_id, hits)
    if effective:
        return _GraphAndResolved(
            _neo4j_graph_context_for_work(neo4j, effective),
            effective,
        )
    return _GraphAndResolved(
        {
            "methods": [],
            "datasets": [],
            "semantic_available": False,
            "context_work_id": None,
            "degraded": ["no_resolved_work"],
            "error": None,
        },
        None,
    )


class _RetrievalTraceIn(NamedTuple):
    emb_trace: dict[str, Any]
    hits: list[dict[str, Any]]
    filter_work_id: str | None
    resolved_work_id: str | None
    qdrant_collection: str
    top_k: int
    citations_returned: int


def _retrieval_trace_payload(
    inp: _RetrievalTraceIn,
    *,
    query_preview: str | None = None,
    answer_synthesis: dict[str, Any] | None = None,
    extra_degraded: list[str] | None = None,
    workspace_id: str | None = None,
    retrieval_mode: Literal["vector", "hybrid"] = "vector",
    retrieval_policy: str | None = None,
) -> dict[str, Any]:
    trace_degraded: list[str] = []
    if len(inp.hits) == 0:
        trace_degraded.append("no_retrieval_hits")
    top_scores: list[float | None] = []
    for h in inp.hits[: min(8, len(inp.hits))]:
        s = h.get("score")
        top_scores.append(float(s) if s is not None else None)
    qprev = (query_preview or "").strip()
    if len(qprev) > 240:
        qprev = qprev[:240] + "…"
    trace_degraded.extend(extra_degraded or [])
    syn = answer_synthesis or {
        "mode": "deterministic_snippets",
        "second_stage_llm": False,
    }
    policy = retrieval_policy or "section_boost_v1;back_matter_deprioritized;oversample_then_top_k"
    out: dict[str, Any] = {
        "embedding": inp.emb_trace,
        "hit_count": len(inp.hits),
        "filter_work_id": inp.filter_work_id,
        "resolved_work_id": inp.resolved_work_id,
        "qdrant_collection": inp.qdrant_collection,
        "top_k_requested": inp.top_k,
        "citations_returned": inp.citations_returned,
        "top_hit_scores": top_scores,
        "query_preview": qprev or None,
        "answer_synthesis": syn,
        "retrieval_mode": retrieval_mode,
        "retrieval_policy": policy,
        "degraded": trace_degraded,
    }
    ws = (workspace_id or "").strip()
    if ws:
        out["workspace_id"] = ws
    return out


def _try_query_answer_llm(
    question: str,
    citations: list[dict[str, Any]],
    settings: Settings,
) -> tuple[str | None, dict[str, Any]]:
    """Optional second-stage LLM: paraphrase grounded on citation excerpts only."""

    if not settings.query_answer_llm_enabled:
        return None, {}
    api_key = settings.extraction_llm_api_key
    if not api_key:
        return None, {"skipped": True, "reason": "no_api_key"}

    ctx_lines: list[str] = []
    for i, c in enumerate(citations[:10], start=1):
        ex = (c.get("excerpt") or "").strip()
        if not ex:
            continue
        meta: list[str] = []
        if c.get("section_path"):
            meta.append(f"section={c['section_path']}")
        if c.get("chunk_fingerprint"):
            meta.append(f"chunk={c['chunk_fingerprint']}")
        ctx_lines.append(f"[{i}] ({', '.join(meta) if meta else 'excerpt'}) {ex}")
    if not ctx_lines:
        return None, {"skipped": True, "reason": "no_citation_text"}

    system = (
        "You are a scientific assistant. Answer ONLY using the numbered excerpts. "
        "If excerpts are insufficient, say so briefly. Do not invent citations, DOIs, "
        "or facts that are not supported by the excerpts."
    )
    user = f"Question:\n{question}\n\nExcerpts:\n" + "\n".join(ctx_lines)
    try:
        timeout = min(float(settings.extraction_llm_timeout_seconds), 120.0)
        client = OpenAI(
            api_key=api_key,
            base_url=settings.extraction_llm_base_url,
            timeout=timeout,
        )
        resp = client.chat.completions.create(
            model=settings.extraction_llm_model,
            temperature=float(settings.query_answer_llm_temperature),
            max_tokens=int(settings.query_answer_llm_max_tokens),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = (resp.choices[0].message.content or "").strip()
        if not text:
            return None, {"error": "empty_llm_response"}
        return text, {"model": settings.extraction_llm_model}
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"{type(exc).__name__}: {exc}"}


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
    """Embed query, search Qdrant with oversampling, deprioritize back-matter sections."""

    vec, emb_trace = _embed_query(question, settings)
    fetch_limit = min(max(top_k * 8, top_k), 48)
    hits_raw = qdrant_chunks.search_similar(
        vector=vec,
        limit=fetch_limit,
        work_id=work_id,
        work_ids=work_ids,
        workspace_id=workspace_id,
    )
    hits = _rank_hits_for_answer(hits_raw, top_k=top_k)
    return vec, emb_trace, hits


def _sanitize_fulltext_query(text: str) -> str:
    """Keep Lucene-friendly tokens for ``db.index.fulltext.queryNodes``."""

    raw = (text or "").strip()
    if not raw:
        return ""
    t = re.sub(r"[^a-zA-Z0-9\s\-.]", " ", raw)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:220] if t else raw[:220]


def _hit_fingerprint_key(hit: dict[str, Any]) -> str:
    fp = hit.get("chunk_fingerprint")
    if fp:
        return str(fp)
    return str(hit.get("id") or "")


def _reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    *,
    k: int = 60,
    top_n: int = 12,
) -> list[dict[str, Any]]:
    """RRF over chunk-level ranked lists; dedupe by chunk fingerprint."""

    scores: dict[str, float] = {}
    by_fp: dict[str, dict[str, Any]] = {}
    for lst in ranked_lists:
        for rank, hit in enumerate(lst, start=1):
            fp = _hit_fingerprint_key(hit)
            if not fp:
                continue
            scores[fp] = scores.get(fp, 0.0) + 1.0 / (k + rank)
            prev = by_fp.get(fp)
            if prev is None or float(hit.get("score") or 0.0) > float(prev.get("score") or 0.0):
                by_fp[fp] = hit
    ordered = sorted(by_fp.keys(), key=lambda fp: scores[fp], reverse=True)
    out: list[dict[str, Any]] = []
    for fp in ordered[:top_n]:
        h = dict(by_fp[fp])
        h["rrf_score"] = scores[fp]
        out.append(h)
    return out


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
    """Vector chunks + Neo4j fulltext works + CITES-expanded works → RRF merge (Wave Q)."""

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
    q_ft = _sanitize_fulltext_query(question)
    ft_works: list[tuple[str, float]] = []
    graph_works: list[str] = []
    if q_ft:
        ft_works = neo4j.fulltext_search_work_ids(q_ft, limit=20)
    seeds: list[str] = []
    for h in hits_vector[:10]:
        wid = h.get("work_id")
        if wid:
            seeds.append(str(wid))
    for wid, _s in ft_works[:12]:
        seeds.append(wid)
    seeds = list(dict.fromkeys(seeds))
    excl: set[str] = set()
    if work_id:
        excl.add(str(work_id).strip())
    graph_works = neo4j.cites_neighbor_work_ids(seeds, exclude_ids=excl, limit=60)

    lanes: list[list[dict[str, Any]]] = [hits_vector]
    ft_ids = [w for w, _s in ft_works][:18]
    if ft_ids:
        raw_ft = qdrant_chunks.search_similar(
            vector=vec,
            limit=36,
            work_id=None,
            work_ids=ft_ids,
            workspace_id=workspace_id,
        )
        lanes.append(_rank_hits_for_answer(raw_ft, top_k=max(top_k * 4, 16)))
    gid_set = set(ft_ids)
    graph_ids = [w for w in graph_works if w not in gid_set][:18]
    if graph_ids:
        raw_g = qdrant_chunks.search_similar(
            vector=vec,
            limit=28,
            work_id=None,
            work_ids=graph_ids,
            workspace_id=workspace_id,
        )
        lanes.append(_rank_hits_for_answer(raw_g, top_k=max(top_k * 3, 12)))

    fused = _reciprocal_rank_fusion(lanes, k=60, top_n=top_k)
    hybrid_meta = {
        "fulltext_work_hits": len(ft_works),
        "graph_extra_works": len(graph_works),
        "fusion_lanes": len(lanes),
        "fulltext_query": q_ft or None,
    }
    emb_out = {**emb_trace, "hybrid": hybrid_meta}
    return vec, emb_out, fused


def _workspace_scope_work_ids(
    neo4j: Neo4jGraphStore, workspace_id: str
) -> tuple[list[str] | None, dict[str, Any]]:
    """
    Returns (work_ids, meta) for Qdrant filter.
    None work_ids => do not apply workspace filter (invalid / unused).
    Empty list => workspace resolved but no member works (caller should skip Qdrant search).
    """

    wid = (workspace_id or "").strip()
    if not wid:
        return None, {}
    row = neo4j.workspace_get(wid)
    if not row:
        return [], {
            "workspace_id": wid,
            "workspace_missing": True,
            "workspace_scope_work_count": 0,
        }
    ids = [str(x) for x in (row.get("work_ids") or []) if x]
    return ids, {"workspace_id": wid, "workspace_scope_work_count": len(ids)}


def answer_query(
    question: str,
    *,
    settings: Settings | None = None,
    stores: StoreRegistry | None = None,
    work_id: str | None = None,
    workspace_id: str | None = None,
    top_k: int = 5,
    mode: Literal["vector", "hybrid"] = "vector",
) -> GroundedAnswer:
    """
    MVP GraphRAG path: embed question, search Qdrant, attach chunk citations, add Neo4j context.

    ``mode="hybrid"`` (Wave Q): RRF over dense chunk search + Neo4j full-text work hits +
    vector search scoped to CITES-expanded works.

    No second-stage LLM: answer is a short deterministic summary over retrieved snippets.
    """

    s = settings or get_settings()
    owned_neo4j: Neo4jGraphStore | None = None
    if stores is None:
        # Backward-compatible fallback for non-API callers.
        owned_neo4j = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
        owned_qdrant = QdrantChunkStore(
            s.qdrant_url,
            s.qdrant_collection,
            vector_dim=resolve_embedding_dim(embedding_model=s.embedding_model),
        )
        neo4j = owned_neo4j
        qdrant_chunks = owned_qdrant
    else:
        neo4j = stores.neo4j
        qdrant_chunks = stores.qdrant_chunks
    mode_norm: Literal["vector", "hybrid"] = (
        "hybrid" if (mode or "").strip().lower() == "hybrid" else "vector"
    )
    ws_meta: dict[str, Any] = {}
    ws_scope_payload_miss: str | None = None
    work_ids_filter: list[str] | None = None
    wid_param = (work_id or "").strip() or None
    ws_param = (workspace_id or "").strip() or None
    if ws_param and not wid_param:
        work_ids_filter, ws_meta = _workspace_scope_work_ids(neo4j, ws_param)

    if work_ids_filter is not None and len(work_ids_filter) == 0:
        _, emb_trace = _embed_query(question, s)
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
            if mode_norm == "hybrid":
                _, emb_trace_fb, hits = _hybrid_hits_for_answer(
                    question=question,
                    settings=s,
                    neo4j=neo4j,
                    qdrant_chunks=qdrant_chunks,
                    work_id=None,
                    work_ids=q_work_ids,
                    top_k=top_k,
                    workspace_id=None,
                )
            else:
                _, emb_trace_fb, hits = _qdrant_hits_for_answer(
                    question=question,
                    settings=s,
                    qdrant_chunks=qdrant_chunks,
                    work_id=None,
                    work_ids=q_work_ids,
                    top_k=top_k,
                    workspace_id=None,
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

    synthesis: dict[str, Any] = {
        "mode": "deterministic_snippets",
        "second_stage_llm": False,
    }
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

    rpolicy = (
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
        retrieval_policy=rpolicy,
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
