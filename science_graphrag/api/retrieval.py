"""Vector retrieval + Neo4j graph context for query-time (Phase 5 MVP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from neo4j import GraphDatabase, NotificationClassification

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.storage.qdrant_store import QdrantChunkStore


@dataclass
class GroundedAnswer:
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


def _neo4j_semantic_neighborhood(settings: Settings, work_id: str) -> dict[str, Any]:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        notifications_disabled_classifications=[NotificationClassification.UNRECOGNIZED],
    )
    methods: list[str] = []
    datasets: list[str] = []
    try:
        with driver.session() as session:
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
    finally:
        driver.close()
    return {"methods": sorted(set(methods)), "datasets": sorted(set(datasets))}


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
    vec, emb_trace = _embed_query(question, s)
    qstore = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=len(vec))
    hits = qstore.search_similar(vector=vec, limit=top_k, work_id=work_id)
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

    graph: dict[str, Any] = {"methods": [], "datasets": []}
    effective_work = work_id or (hits[0].get("work_id") if hits else None)
    if effective_work:
        try:
            graph = _neo4j_semantic_neighborhood(s, effective_work)
        except Exception:  # noqa: BLE001
            graph = {"methods": [], "datasets": [], "error": "neo4j_unavailable"}

    if snippets:
        joined = " ".join(snippets[:3])
        answer = (
            "Retrieved context (not LLM-paraphrased): "
            + joined[:1200]
            + ("…" if len(joined) > 1200 else "")
        )
    else:
        answer = "No retrieved chunks; ingest documents or check Qdrant collection."

    trace = {
        "embedding": emb_trace,
        "hit_count": len(hits),
        "filter_work_id": work_id,
        "resolved_work_id": effective_work,
    }
    return GroundedAnswer(
        answer=answer,
        citations=citations,
        graph_context=graph,
        retrieval_trace=trace,
    )
