"""Ingestion orchestration facade and legacy-compatible entrypoints."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import Retrying, stop_after_attempt, wait_exponential

from science_graphrag.artifacts.protocols import ArtifactStorePort
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.artifact_layout import canonical_article_md_rel
from science_graphrag.ingestion.cache_policy import article_slug as _article_slug
from science_graphrag.ingestion.cache_policy import canonical_article_rel as _canonical_article_rel
from science_graphrag.ingestion.cache_policy import (
    canonical_diagnostics_rel as _canonical_diagnostics_rel,
)
from science_graphrag.ingestion.markdown_extraction import markdown_from_path
from science_graphrag.ingestion.reference_citations import (
    maybe_link_openalex_arxiv_version,
    normalize_arxiv_id,
    normalized_title_for_fingerprint,
    openalex_lookup_with_retry,
    persist_reference_citation,
    resolve_work_id,
    venue_id,
)
from science_graphrag.ingestion.session_wiring import (
    sql_commit_if_session as _sql_commit_if_session,
)
from science_graphrag.ingestion.stage_context import IngestRunContext, build_ingest_run_context
from science_graphrag.storage.models_orm import DocumentRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.raw_blob_store import RawBlobStorePort, build_raw_blob_store
from science_graphrag.storage.s3_artifact_store import build_artifact_store
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.pipeline")

_openalex_lookup_with_retry = openalex_lookup_with_retry
_resolve_work_id = resolve_work_id
_venue_id = venue_id
_normalize_arxiv_id = normalize_arxiv_id
_normalized_title_for_fingerprint = normalized_title_for_fingerprint
_persist_reference_citation = persist_reference_citation
_maybe_link_openalex_arxiv_version = maybe_link_openalex_arxiv_version
_markdown_from_path = markdown_from_path


@dataclass(slots=True)
class IngestSource:
    """Input source for one ingest pipeline run."""

    path: Path


@dataclass(slots=True)
class IngestResult:
    """Minimal ingest output with document/work identifiers."""

    document_id: str
    work_id: str


class SkippedDuplicateIngestError(Exception):
    """Raised when ``skip_existing_sha`` and the file hash is already in ``documents``."""

    def __init__(self, *, document_id: str, sha256: str) -> None:
        self.document_id = document_id
        self.sha256 = sha256
        super().__init__(f"skip duplicate sha256={sha256} document_id={document_id}")


def _retry_call(func, *args, **kwargs):
    runner = Retrying(
        wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True
    )
    return runner(func, *args, **kwargs)


def _resolve_document_id_for_sha(
    session: Session,
    sha256_hex: str,
    *,
    skip_existing_sha: bool,
    force_new_document: bool,
) -> tuple[str, bool]:
    """
    Pick ``document_id`` for ingest.

    Returns:
        (document_id, reused_existing) — reused_existing True when re-ingesting same bytes.
    """

    if force_new_document:
        return str(uuid.uuid4()), False
    row = (
        session.execute(
            select(DocumentRecord)
            .where(DocumentRecord.sha256 == sha256_hex)
            .order_by(DocumentRecord.created_at.desc()),
        )
        .scalars()
        .first()
    )
    if row is None:
        return str(uuid.uuid4()), False
    if skip_existing_sha:
        raise SkippedDuplicateIngestError(document_id=row.id, sha256=sha256_hex)
    return row.id, True


def _write_markdown_artifact(
    *,
    settings: Settings,
    document_id: str,
    source_path: Path,
    markdown: str,
    extraction_mode: str,
    artifact_store: ArtifactStorePort | None = None,
) -> Path:
    """Write canonical ``ingestion/{document_id}/article.md`` plus legacy slug paths."""
    store = artifact_store or build_artifact_store(settings)
    slug = _article_slug(source_path)
    legacy_rel = Path("ingestion") / document_id / slug / "article.md"
    header = f"<!-- source={source_path.name} extraction_mode={extraction_mode} -->\n\n"
    body = header + markdown
    store.write_text(canonical_article_md_rel(document_id), body)
    store.write_text(_canonical_article_rel(source_path), body)
    return store.write_text(legacy_rel, body)


def _write_extraction_diagnostics_json(
    *,
    settings: Settings,
    document_id: str,
    source_path: Path,
    diagnostics_json: str,
    artifact_store: ArtifactStorePort | None = None,
) -> Path:
    store = artifact_store or build_artifact_store(settings)
    slug = _article_slug(source_path)
    artifact_rel = Path("ingestion") / document_id / slug / "extraction_diagnostics.json"
    store.write_text(_canonical_diagnostics_rel(source_path), diagnostics_json)
    return store.write_text(artifact_rel, diagnostics_json)


def run_ingest_pipeline(
    ctx: IngestRunContext,
    source: IngestSource,
    *,
    bypass_markdown_cache: bool = False,
) -> IngestResult:
    """Run ingestion pipeline in an already constructed runtime context."""
    doc_id, work_id = ingest_document(
        source.path,
        settings=ctx.settings,
        session=ctx.session,
        skip_existing_sha=False,
        force_new_document=False,
        ingest_workspace_ids=ctx.ingest_workspace_ids,
        job_id=ctx.job_id,
        parent_job_id=ctx.parent_job_id,
        stage_session_factory=ctx.stage_session_factory,
        stage_event_publisher=ctx.stage_event_publisher,
        stage_progress_publisher=ctx.stage_progress_publisher,
        bypass_markdown_cache=bypass_markdown_cache,
    )
    return IngestResult(document_id=doc_id, work_id=work_id)


def run_ingest_from_file(
    path: Path,
    *,
    settings: Settings,
    session: Session | None = None,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    parent_job_id: str | None = None,
    stage_session_factory: Any | None = None,
    stage_event_publisher: Any | None = None,
    stage_progress_publisher: Any | None = None,
    bypass_markdown_cache: bool = False,
) -> IngestResult:
    """Ingest one file using context-builder wiring and auto-close semantics."""
    ctx = build_ingest_run_context(
        settings=settings,
        source_path=path,
        session=session,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
        stage_progress_publisher=stage_progress_publisher,
    )
    try:
        return run_ingest_pipeline(
            ctx, IngestSource(path=path), bypass_markdown_cache=bypass_markdown_cache
        )
    finally:
        ctx.close()


def run_ingest_from_job(
    path: Path,
    *,
    settings: Settings,
    session: Session | None = None,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    parent_job_id: str | None = None,
    stage_session_factory: Any | None = None,
    stage_event_publisher: Any | None = None,
    stage_progress_publisher: Any | None = None,
    bypass_markdown_cache: bool = False,
) -> IngestResult:
    """Backward-compatible job entrypoint alias for file ingest."""
    return run_ingest_from_file(
        path,
        settings=settings,
        session=session,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
        stage_progress_publisher=stage_progress_publisher,
        bypass_markdown_cache=bypass_markdown_cache,
    )


def ingest_document(
    path: Path,
    *,
    settings: Settings | None = None,
    session: Session | None = None,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    parent_job_id: str | None = None,
    stage_session_factory: Any | None = None,
    stage_event_publisher: Any | None = None,
    stage_progress_publisher: Any | None = None,
    raw_blob_store: RawBlobStorePort | None = None,
    bypass_markdown_cache: bool = False,
) -> tuple[str, str]:
    """
    Ingest one PDF or text file. Returns (document_id, work_id).

    With a SQL ``session``, the same file bytes (``sha256``) reuse the existing ``document_id``
    by default, Qdrant rows for that id are replaced, and Postgres metadata is updated.
    Use ``skip_existing_sha`` to no-op when the hash exists; ``force_new_document`` for a new row
    every time (no SQL dedup — e.g. benchmarks with ``session is None``).
    """
    settings = settings or get_settings()
    blob_store = raw_blob_store or build_raw_blob_store(settings)
    sha, _stored = blob_store.store_file(path)
    if session is None:
        doc_id, reused_doc = str(uuid.uuid4()), False
    else:
        doc_id, reused_doc = _resolve_document_id_for_sha(
            session,
            sha,
            skip_existing_sha=skip_existing_sha,
            force_new_document=force_new_document,
        )

    from science_graphrag.ingestion.document_orchestrator import (
        DocumentOrchestrationDeps,
        run_document_orchestration,
    )

    return run_document_orchestration(
        path=path,
        settings=settings,
        session=session,
        doc_id=doc_id,
        sha=sha,
        reused_doc=reused_doc,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
        stage_progress_publisher=stage_progress_publisher,
        bypass_markdown_cache=bypass_markdown_cache,
        deps=DocumentOrchestrationDeps(
            markdown_from_path=_markdown_from_path,
            write_markdown_artifact=_write_markdown_artifact,
            write_extraction_diagnostics_json=_write_extraction_diagnostics_json,
            openalex_lookup_with_retry=_openalex_lookup_with_retry,
            resolve_work_id=_resolve_work_id,
            venue_id=_venue_id,
            persist_reference_citation=_persist_reference_citation,
            maybe_link_openalex_arxiv_version=_maybe_link_openalex_arxiv_version,
            normalize_arxiv_id=_normalize_arxiv_id,
            normalized_title_for_fingerprint=_normalized_title_for_fingerprint,
            retry_call=_retry_call,
            sql_commit_if_session=_sql_commit_if_session,
            build_artifact_store=build_artifact_store,
            neo4j_store_class=Neo4jGraphStore,
            logger=logger,
        ),
    )
