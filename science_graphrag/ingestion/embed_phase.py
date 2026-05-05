"""Embed phase orchestration for ingest_document."""

from __future__ import annotations

from typing import Any

from science_graphrag.config import Settings
from science_graphrag.domain.models import WorkDraft
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.observability.phoenix_tracer import chain_span, embeddings_span
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


def run_ingest_embed_qdrant_phase(
    *,
    settings: Settings,
    document_id: str,
    work_id: str,
    doc_chunks: list[Any],
    claim_rows: list[Any],
    authorships: list[Any],
    draft: WorkDraft,
    ingest_workspace_ids: list[str] | None,
    st: Any,
    reused_doc: bool,
    retry_call,
    logger,
) -> None:
    """Vectorize chunks + work summary and upsert Qdrant (after Neo4j is closed)."""
    total_steps = 4 if (settings.claims_extraction_enabled and claim_rows) else 3
    step = 0

    def _embed_bump(detail: str) -> None:
        nonlocal step
        step += 1
        st.metric("subprogress_current", step)
        st.metric("subprogress_total", total_steps)
        st.metric("detail_message", detail)
        st.flush_progress()

    embedder = resolve_embedder(settings)
    chunk_texts = [c.text for c in doc_chunks]
    embedding_model = resolve_embedding_model_label(settings)
    _embed_bump("Embedding body chunks…")
    with embeddings_span(
        "ingest.embed.vectorize_chunks",
        {
            "embedding.model_name": embedding_model,
            "embedding.dim": embedder.dim,
            "embedding.input_count": len(chunk_texts),
        },
    ):
        vectors = embedder.embed(chunk_texts)
    first_author = ""
    if authorships:
        ordered_auth = sorted(authorships, key=lambda x: x.author_position or 0)
        first_author = (ordered_auth[0].author_raw_name or "").strip()
    summary_text = f"{draft.title or ''}\n{draft.abstract or ''}\n{first_author}"[:8000]
    _embed_bump("Embedding work summary…")
    with embeddings_span(
        "ingest.embed.vectorize_work_summary",
        {
            "embedding.model_name": embedding_model,
            "embedding.dim": embedder.dim,
            "embedding.input_count": 1,
        },
    ):
        w_summary_vec = embedder.embed([summary_text])[0]
    qw = QdrantWorkEmbeddingStore(
        settings.qdrant_url,
        settings.qdrant_work_embeddings_collection,
        vector_dim=embedder.dim,
    )
    retry_call(
        qw.upsert_work_summary,
        work_id=work_id,
        vector=w_summary_vec,
        embedding_model=embedding_model,
        workspace_ids=ingest_workspace_ids or [],
        title=draft.title,
        publication_year=draft.publication_year,
        doi=draft.doi,
        arxiv_id=draft.arxiv_id,
        first_author_normalized=first_author,
        embedding_kind="work_summary_v1",
    )
    q = QdrantChunkStore(
        settings.qdrant_url,
        settings.qdrant_collection,
        vector_dim=embedder.dim,
    )
    removed = retry_call(q.delete_points_by_document_id, document_id=document_id)
    if removed and reused_doc:
        logger.info(
            "qdrant removed %s point(s) before re-ingest document_id=%s",
            removed,
            document_id,
        )
    _embed_bump("Upserting chunk vectors to Qdrant…")
    with chain_span(
        "ingest.embed.qdrant_chunks",
        {
            "chunks": len(doc_chunks),
            "embedding": embedding_model,
            "db.system": "qdrant",
            "db.collection.name": settings.qdrant_collection,
            "db.operation": "upsert",
            "vector.dim": embedder.dim,
            "vector.count": len(vectors),
        },
    ):
        retry_call(
            q.upsert_document_chunks,
            work_id=work_id,
            document_id=document_id,
            document_chunks=doc_chunks,
            vectors=vectors,
            embedding_model=embedding_model,
            workspace_ids=ingest_workspace_ids or [],
        )
    if settings.claims_extraction_enabled and claim_rows:
        _embed_bump("Embedding claims to Qdrant…")
        with chain_span(
            "ingest.embed.qdrant_claims",
            {
                "claims": len(claim_rows),
                "embedding": embedding_model,
                "db.system": "qdrant",
                "db.collection.name": settings.qdrant_claims_collection,
                "db.operation": "upsert",
                "vector.dim": embedder.dim,
                "vector.count": len(claim_rows),
            },
        ):
            qc = QdrantClaimsStore(
                settings.qdrant_url,
                settings.qdrant_claims_collection,
                vector_dim=embedder.dim,
            )
            retry_call(qc.delete_points_by_work_id, work_id=work_id)
            retry_call(
                qc.upsert_claims,
                work_id=work_id,
                claims=claim_rows,
                embedder=embedder,
                embedding_model=embedding_model,
            )
    st.metric("chunks", len(doc_chunks))
    st.metric("embedding_dim", embedder.dim)
