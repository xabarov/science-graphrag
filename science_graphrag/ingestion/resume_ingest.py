"""Resume late-stage ingest (embed/Qdrant) for documents with artifacts + SQL row."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from science_graphrag.domain.models import WorkDraft
from science_graphrag.embeddings.errors import EmbeddingCallError, EmbeddingNonRetryableHttpError
from science_graphrag.ingestion._pipeline_impl import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.artifact_layout import canonical_normalized_md_rel
from science_graphrag.ingestion.checkpoint import (
    mark_stage_completed,
    mark_stage_failed,
    parse_checkpoint,
    serialize_checkpoint,
)
from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord
from science_graphrag.utils.project_logging import get_logger

if TYPE_CHECKING:
    from science_graphrag.config import Settings

log = get_logger("ingestion.resume")


def minimal_work_draft_from_normalized_markdown(normalized: str) -> WorkDraft:
    """Best-effort WorkDraft for embed summary when full LLM draft is unavailable."""
    title: str | None = None
    for line in normalized.splitlines():
        s = line.strip()
        if s.startswith("# "):
            title = s[2:].strip() or None
            break
    abstract: str | None = None
    m = re.search(
        r"(?is)^##\s+abstract\s*$(.+?)(?=^##\s|\Z)",
        normalized,
        flags=re.MULTILINE,
    )
    if m:
        abstract = m.group(1).strip() or None
    if not abstract and len(normalized) > 200:
        abstract = normalized[:4000]
    return WorkDraft(title=title, abstract=abstract)


def resume_document_embed_phase(
    *,
    document_id: str,
    settings: "Settings",
    session: Session,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    stage_session_factory: Any = None,
    stage_event_publisher: Any = None,
) -> str:
    """
    Re-run chunking + embeddings + Qdrant upsert for an existing ``document_id``.

    Expects ``normalized.md`` under ``settings.artifact_root`` and ``DocumentRecord.work_id``.
    Updates ``ingest_checkpoint_json`` and appends an ``IngestionRunRecord`` on success/failure.
    """

    row = session.get(DocumentRecord, document_id)
    if row is None:
        raise ValueError(f"document_id not found: {document_id}")
    work_id = row.work_id
    if not work_id:
        raise ValueError(f"document {document_id} has no work_id; run full ingest first")

    norm_path = Path(settings.artifact_root) / canonical_normalized_md_rel(document_id)
    if not norm_path.is_file():
        raise FileNotFoundError(f"missing normalized artifact: {norm_path}")
    normalized = norm_path.read_text(encoding="utf-8")

    doc_chunks = dedupe_chunks_for_embedding(
        chunk_document_for_retrieval(
            normalized,
            target_tokens=settings.chunk_target_tokens,
            overlap_tokens=settings.chunk_overlap_tokens,
        ),
    )
    draft = minimal_work_draft_from_normalized_markdown(normalized)
    ckpt = parse_checkpoint(row.ingest_checkpoint_json)
    ingest_run = IngestionRunRecord(
        document_id=document_id,
        status="running",
        finished_at=None,
    )
    session.add(ingest_run)
    session.flush()

    reused_doc = True
    try:
        with stage(
            job_id,
            IngestStage.EMBED,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
        ) as st:
            run_ingest_embed_qdrant_phase(
                settings=settings,
                document_id=document_id,
                work_id=work_id,
                doc_chunks=doc_chunks,
                claim_rows=[],
                authorships=[],
                draft=draft,
                ingest_workspace_ids=ingest_workspace_ids,
                st=st,
                reused_doc=reused_doc,
            )
    except Exception as exc:
        retryable = True
        if isinstance(exc, EmbeddingNonRetryableHttpError):
            retryable = False
        elif isinstance(exc, EmbeddingCallError):
            retryable = exc.retryable
        mark_stage_failed(ckpt, IngestStage.EMBED, error=str(exc), retryable=retryable)
        row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
        ingest_run.status = "failed_retryable" if retryable else "failed_terminal"
        ingest_run.error_message = str(exc)[:8000]
        ingest_run.finished_at = datetime.now(UTC)
        session.commit()
        raise
    mark_stage_completed(ckpt, IngestStage.EMBED)
    row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
    ingest_run.status = "completed"
    ingest_run.finished_at = datetime.now(UTC)
    session.commit()
    log.info("resume embed completed document_id=%s work_id=%s", document_id, work_id)
    return work_id
