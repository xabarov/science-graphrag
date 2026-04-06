"""Vector retrieval + Neo4j graph context for query-time (Phase 5 MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

from neo4j import GraphDatabase, NotificationClassification

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.storage.qdrant_store import QdrantChunkStore


@dataclass
class GroundedAnswer:
    """Deterministic retrieval result for POST /v1/query (no second-stage LLM)."""

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


def _prefer_non_back_matter_hits(
    hits: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Keep vector order but move acknowledgment/bibliography-style chunks later."""

    if not hits:
        return []
    primary = [h for h in hits if not _is_likely_back_matter_section(h.get("section_path"))]
    tail = [h for h in hits if _is_likely_back_matter_section(h.get("section_path"))]
    ordered = primary + tail
    return ordered[:top_k]


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
        "answer_synthesis": {
            "mode": "deterministic_snippets",
            "second_stage_llm": False,
        },
        "degraded": trace_degraded,
    }


def _qdrant_hits_for_answer(
    *,
    question: str,
    settings: Settings,
    work_id: str | None,
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
    hits_raw = qstore.search_similar(vector=vec, limit=fetch_limit, work_id=work_id)
    hits = _prefer_non_back_matter_hits(hits_raw, top_k=top_k)
    return vec, emb_trace, hits


def answer_query(
    question: str,
    *,
    settings: Settings | None = None,
    work_id: str | None = None,
    top_k: int = 5,
) -> GroundedAnswer:
    """
    MVP GraphRAG path: embed question, search Qdrant, attach chunk citations, add Neo4j context.

    No second-stage LLM: answer is a short deterministic summary over retrieved snippets.
    """

    s = settings or get_settings()
    _, emb_trace, hits = _qdrant_hits_for_answer(
        question=question,
        settings=s,
        work_id=work_id,
        top_k=top_k,
    )
    citations, snippets = _citations_and_snippets_from_hits(hits)
    graph, resolved_work = _graph_context_for_hits(s, work_id, hits)

    if snippets:
        joined = " ".join(snippets[:3])
        answer = (
            "Retrieved context (not LLM-paraphrased): "
            + joined[:1200]
            + ("…" if len(joined) > 1200 else "")
        )
    else:
        answer = "No retrieved chunks; ingest documents or check Qdrant collection."

    return GroundedAnswer(
        answer=answer,
        citations=citations,
        graph_context=graph,
        retrieval_trace=_retrieval_trace_payload(
            _RetrievalTraceIn(
                emb_trace,
                hits,
                work_id,
                resolved_work,
                s.qdrant_collection,
                top_k,
                len(citations),
            ),
            query_preview=question,
        ),
    )
