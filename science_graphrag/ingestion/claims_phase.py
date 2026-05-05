"""Claims extraction stage helpers for ingestion pipeline."""

from __future__ import annotations

from typing import Any

from science_graphrag.config import Settings
from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.observability.phoenix_tracer import chain_span, llm_span


def run_extract_claims_stage(
    *,
    job_id: str | None,
    stage_session_factory: Any | None,
    stage_event_publisher: Any | None,
    progress_emit: Any | None,
    settings: Settings,
    doc_chunks: list[Any],
    doc_id: str,
    work_id: str,
    retry_call,
    neo,
) -> list[Any]:
    """Run EXTRACT_CLAIMS stage and persist claims into Neo4j."""
    claim_rows: list[Any] = []
    with stage(
        job_id,
        IngestStage.EXTRACT_CLAIMS,
        session_factory=stage_session_factory,
        publisher=stage_event_publisher,
        progress_emit=progress_emit,
        settings=settings,
    ) as st:
        if settings.claims_extraction_enabled:
            chunk_dicts = [
                {
                    "text": c.text,
                    "chunk_fingerprint": c.chunk_fingerprint,
                    "section_path": c.section_path,
                }
                for c in doc_chunks
            ]

            def _claims_batch_progress(idx: int, total_batches: int) -> None:
                st.metric("subprogress_current", idx)
                st.metric("subprogress_total", max(total_batches, 1))
                st.metric("detail_message", f"Claims LLM batch {idx}/{total_batches}")
                st.flush_progress()

            with chain_span(
                "ingest.extract_claims.llm",
                {"document.id": doc_id, "work.id": work_id, "chunks": len(chunk_dicts)},
            ):
                with llm_span(
                    "llm.claims_extraction",
                    {"document.id": doc_id, "work.id": work_id, "chunks": len(chunk_dicts)},
                ):
                    claim_rows = extract_claims_llm(
                        chunk_dicts,
                        work_id,
                        settings,
                        force_benchmark=False,
                        on_batch_progress=_claims_batch_progress,
                    )
            st.metric("claims", len(claim_rows))
            with chain_span(
                "ingest.extract_claims.upsert_claims",
                {
                    "db.system": "neo4j",
                    "db.operation": "merge",
                    "writes.count": len(claim_rows),
                },
            ):
                retry_call(neo.detach_delete_claims_for_work, work_id)
                retry_call(neo.upsert_claims_with_evidence, work_id, claim_rows)
        else:
            st.metric("claims_extraction_enabled", 0)
    return claim_rows
