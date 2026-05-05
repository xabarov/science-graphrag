"""Canonical claims stage wrapper used by ingest orchestration."""

from __future__ import annotations

from typing import Any

from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.claims_phase import run_extract_claims_stage


def run_claims_legacy(ctx: Any, *, work_id: str, chunks: list[Any]) -> list[Any]:
    """Legacy ctx-based claims execution used by stage module tests."""
    with ctx.stage("extract_claims") as st:
        if not ctx.settings.claims_extraction_enabled:
            st.metric("claims_extraction_enabled", 0)
            return []
        chunk_dicts = [
            {
                "text": c.text,
                "chunk_fingerprint": c.chunk_fingerprint,
                "section_path": c.section_path,
            }
            for c in chunks
        ]
        claims = extract_claims_llm(
            chunk_dicts,
            work_id,
            ctx.settings,
            force_benchmark=False,
        )
        st.metric("claims", len(claims))
        return claims


def run_claims_phase(
    *,
    job_id: str | None,
    stage_session_factory: Any | None,
    stage_event_publisher: Any | None,
    progress_emit: Any | None,
    settings: Any,
    doc_chunks: list[Any],
    doc_id: str,
    work_id: str,
    retry_call,
    neo,
) -> list[Any]:
    """Canonical claims execution path via dedicated phase module."""
    return run_extract_claims_stage(
        job_id=job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
        progress_emit=progress_emit,
        settings=settings,
        doc_chunks=doc_chunks,
        doc_id=doc_id,
        work_id=work_id,
        retry_call=retry_call,
        neo=neo,
    )


def run_claims(*args, **kwargs) -> list[Any]:
    """Compatibility wrapper during legacy-to-canonical migration."""
    if args and len(args) == 1 and "work_id" in kwargs and "chunks" in kwargs:
        return run_claims_legacy(args[0], work_id=kwargs["work_id"], chunks=kwargs["chunks"])
    return run_claims_phase(**kwargs)
