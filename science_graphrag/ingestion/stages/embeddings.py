"""Canonical embeddings stage wrapper used by ingest orchestration."""

from __future__ import annotations

from typing import Any

from science_graphrag.embeddings import resolve_embedder
from science_graphrag.ingestion.embed_phase import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.stage_context import IngestStage, stage


def run_embeddings_legacy(ctx: Any, *, texts: list[str]):
    """Legacy ctx-based embeddings execution used by stage module tests."""
    with ctx.stage("embed") as st:
        embedder = resolve_embedder(ctx.settings)
        vectors = embedder.embed(texts)
        st.metric("embedding_dim", embedder.dim)
        return embedder, vectors


def run_embeddings_phase(
    *,
    job_id: str | None,
    stage_session_factory: Any | None,
    stage_event_publisher: Any | None,
    progress_emit: Any | None,
    settings: Any,
    document_id: str,
    work_id: str,
    doc_chunks: list[Any],
    claim_rows: list[Any],
    authorships: list[Any],
    draft: Any,
    ingest_workspace_ids: list[str] | None,
    reused_doc: bool,
    retry_call,
    logger,
) -> None:
    """Canonical embeddings execution path via dedicated phase module."""
    with stage(
        job_id,
        IngestStage.EMBED,
        session_factory=stage_session_factory,
        publisher=stage_event_publisher,
        progress_emit=progress_emit,
        settings=settings,
    ) as st:
        run_ingest_embed_qdrant_phase(
            settings=settings,
            document_id=document_id,
            work_id=work_id,
            doc_chunks=doc_chunks,
            claim_rows=claim_rows,
            authorships=authorships,
            draft=draft,
            ingest_workspace_ids=ingest_workspace_ids,
            st=st,
            reused_doc=reused_doc,
            retry_call=retry_call,
            logger=logger,
        )


def run_embeddings(*args, **kwargs):
    """Compatibility wrapper during legacy-to-canonical migration."""
    if args and len(args) == 1 and "texts" in kwargs:
        return run_embeddings_legacy(args[0], texts=kwargs["texts"])
    return run_embeddings_phase(**kwargs)
