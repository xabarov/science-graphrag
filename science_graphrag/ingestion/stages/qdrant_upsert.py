from __future__ import annotations

from typing import Any

from science_graphrag.embeddings import resolve_embedding_model_label
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


def run_qdrant_upsert(
    ctx,
    *,
    work_id: str,
    document_id: str,
    chunks: list[Any],
    chunk_vectors: list[list[float]],
    work_vector: list[float],
    embedder: Any,
    claim_rows: list[Any],
) -> None:
    emb_label = resolve_embedding_model_label(ctx.settings)
    q_chunks = QdrantChunkStore(
        ctx.settings.qdrant_url,
        ctx.settings.qdrant_collection,
        vector_dim=embedder.dim,
    )
    q_chunks.delete_points_by_document_id(document_id=document_id)
    q_chunks.upsert_document_chunks(
        work_id=work_id,
        document_id=document_id,
        document_chunks=chunks,
        vectors=chunk_vectors,
        embedding_model=emb_label,
        workspace_ids=ctx.ingest_workspace_ids,
    )

    q_work = QdrantWorkEmbeddingStore(
        ctx.settings.qdrant_url,
        ctx.settings.qdrant_work_embeddings_collection,
        vector_dim=embedder.dim,
    )
    q_work.upsert_work_summary(
        work_id=work_id,
        vector=work_vector,
        embedding_model=emb_label,
        workspace_ids=ctx.ingest_workspace_ids,
        title=None,
        publication_year=None,
        doi=None,
        arxiv_id=None,
        first_author_normalized="",
        embedding_kind="work_summary_v1",
    )

    if claim_rows:
        q_claims = QdrantClaimsStore(
            ctx.settings.qdrant_url,
            ctx.settings.qdrant_claims_collection,
            vector_dim=embedder.dim,
        )
        q_claims.delete_points_by_work_id(work_id=work_id)
        q_claims.upsert_claims(
            work_id=work_id,
            claims=claim_rows,
            embedder=embedder,
            embedding_model=emb_label,
            workspace_ids=ctx.ingest_workspace_ids,
        )
