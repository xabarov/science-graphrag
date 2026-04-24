"""Vector retrieval + Neo4j graph context for query-time (Phase 5 MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

from neo4j import GraphDatabase, NotificationClassification

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from openai import OpenAI

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


def _neo4j_graph_context_for_work(settings: Settings, work_id: str) -> dict[str, Any]:
    """
    Neo4j semantic neighborhood for query-time graph_context.

    Returns stable keys for UI: semantic_available, optional error, operational degraded[].
    """

    methods: list[str] = []
    datasets: list[str] = []
    try:
        with GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
        ) as driver:
            with driver.session() as session:
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
        citations.append(
            {
                "rank": rank,
                "score": h.get("score"),
                "work_id": h.get("work_id"),
                "document_id": h.get("document_id"),
                "chunk_fingerprint": h.get("chunk_fingerprint"),
                "section_path": h.get("section_path"),
                "excerpt": text[:600],
            },
        )
        snippets.append(text[:400])
    return citations, snippets


def _effective_work_id(work_id: str | None, hits: list[dict[str, Any]]) -> str | None:
    return work_id or (hits[0].get("work_id") if hits else None)


class _GraphAndResolved(NamedTuple):
    graph_context: dict[str, Any]
    resolved_work_id: str | None


def _graph_context_for_hits(
    settings: Settings,
    work_id: str | None,
    hits: list[dict[str, Any]],
) -> _GraphAndResolved:
    effective = _effective_work_id(work_id, hits)
    if effective:
        return _GraphAndResolved(
            _neo4j_graph_context_for_work(settings, effective),
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
    return {
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
        "retrieval_policy": "section_boost_v1;back_matter_deprioritized;oversample_then_top_k",
        "degraded": trace_degraded,
    }


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
    work_id: str | None,
    work_ids: list[str] | None,
    top_k: int,
) -> tuple[list[float], dict[str, Any], list[dict[str, Any]]]:
    """Embed query, search Qdrant with oversampling, deprioritize back-matter sections."""

    vec, emb_trace = _embed_query(question, settings)
    qstore = QdrantChunkStore(
        settings.qdrant_url,
        settings.qdrant_collection,
        vector_dim=len(vec),
    )
    fetch_limit = min(max(top_k * 8, top_k), 48)
    hits_raw = qstore.search_similar(vector=vec, limit=fetch_limit, work_id=work_id, work_ids=work_ids)
    hits = _rank_hits_for_answer(hits_raw, top_k=top_k)
    return vec, emb_trace, hits


def _workspace_scope_work_ids(settings: Settings, workspace_id: str) -> tuple[list[str] | None, dict[str, Any]]:
    """
    Returns (work_ids, meta) for Qdrant filter.
    None work_ids => do not apply workspace filter (invalid / unused).
    Empty list => workspace resolved but no member works (caller should skip Qdrant search).
    """

    wid = (workspace_id or "").strip()
    if not wid:
        return None, {}
    store = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        row = store.workspace_get(wid)
        if not row:
            return [], {"workspace_id": wid, "workspace_missing": True, "workspace_scope_work_count": 0}
        ids = [str(x) for x in (row.get("work_ids") or []) if x]
        return ids, {"workspace_id": wid, "workspace_scope_work_count": len(ids)}
    finally:
        store.close()


def answer_query(
    question: str,
    *,
    settings: Settings | None = None,
    work_id: str | None = None,
    workspace_id: str | None = None,
    top_k: int = 5,
) -> GroundedAnswer:
    """
    MVP GraphRAG path: embed question, search Qdrant, attach chunk citations, add Neo4j context.

    No second-stage LLM: answer is a short deterministic summary over retrieved snippets.
    """

    s = settings or get_settings()
    ws_meta: dict[str, Any] = {}
    work_ids_filter: list[str] | None = None
    wid_param = (work_id or "").strip() or None
    ws_param = (workspace_id or "").strip() or None
    if ws_param and not wid_param:
        work_ids_filter, ws_meta = _workspace_scope_work_ids(s, ws_param)

    if work_ids_filter is not None and len(work_ids_filter) == 0:
        _, emb_trace = _embed_query(question, s)
        hits = []
        emb_trace = {**emb_trace, **ws_meta}
    else:
        q_work_ids = None if wid_param else (work_ids_filter if work_ids_filter and len(work_ids_filter) > 0 else None)
        _, emb_trace, hits = _qdrant_hits_for_answer(
            question=question,
            settings=s,
            work_id=wid_param,
            work_ids=q_work_ids,
            top_k=top_k,
        )
        if ws_meta:
            emb_trace = {**emb_trace, **ws_meta}

    citations, snippets = _citations_and_snippets_from_hits(hits)
    graph, resolved_work = _graph_context_for_hits(s, wid_param, hits)

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
    )
    if ws_meta:
        trace_payload = {**trace_payload, **ws_meta}

    return GroundedAnswer(
        answer=answer,
        citations=citations,
        graph_context=graph,
        retrieval_trace=trace_payload,
    )
