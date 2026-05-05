"""Ingestion orchestration facade and legacy-compatible entrypoints."""

from __future__ import annotations

import re
import uuid
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry import trace as trace_api
from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import Retrying, retry, stop_after_attempt, wait_exponential

from science_graphrag.artifacts.protocols import ArtifactStorePort
from science_graphrag.config import Settings, get_settings
from science_graphrag.dedup.entity_ingest_conflict_check import (
    enqueue_entity_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.dedup.ingest_conflict_check import (
    enqueue_author_near_duplicate_conflicts_on_ingest,
    enqueue_work_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.domain.models import ReferenceDraft, WorkDraft
from science_graphrag.embeddings import resolve_embedding_model_label
from science_graphrag.embeddings.errors import EmbeddingCallError, EmbeddingNonRetryableHttpError
from science_graphrag.embeddings.preflight import probe_embeddings
from science_graphrag.ingestion.artifact_layout import (
    canonical_article_md_rel,
    canonical_normalized_md_rel,
    strip_ingest_artifact_header,
)
from science_graphrag.ingestion.cache_policy import article_slug as _article_slug
from science_graphrag.ingestion.cache_policy import canonical_article_rel as _canonical_article_rel
from science_graphrag.ingestion.cache_policy import (
    canonical_diagnostics_rel as _canonical_diagnostics_rel,
)
from science_graphrag.ingestion.cache_policy import (
    read_cached_markdown,
)
from science_graphrag.ingestion.cache_policy import slug as _slug
from science_graphrag.ingestion.checkpoint import (
    default_checkpoint,
    mark_stage_completed,
    mark_stage_failed,
    parse_checkpoint,
    serialize_checkpoint,
)
from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval_from_settings,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.claims_phase import run_extract_claims_stage
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.document_runtime import file_timeout
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
    strip_repeated_boilerplate,
)
from science_graphrag.ingestion.embed_phase import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.enrichment.openalex import (
    arxiv_id_from_openalex_ids,
    draft_from_openalex,
    fetch_work_by_doi,
)
from science_graphrag.ingestion.institution_nodes import institution_nodes_from_authorships
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.ingestion.markdown_fence import strip_whole_document_markdown_fence
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.orchestrator import BatchDeps, run_batch_ingest
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.progress_store import (
    append_progress,
    default_progress_file,
    load_progress,
)
from science_graphrag.ingestion.session_wiring import (
    sql_commit_if_session as _sql_commit_if_session,
)
from science_graphrag.ingestion.stage_context import (
    IngestRunContext,
    IngestStage,
    build_ingest_run_context,
    stage,
)
from science_graphrag.ingestion.stage_graph import (
    build_runtime_state,
    load_checkpoint_from_session,
)
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched
from science_graphrag.ingestion.vl_pdf import VLPDFProcessor
from science_graphrag.observability.phoenix_tracer import (
    OpenInferenceAttributes,
    SpanAttributes,
    chain_span,
    init_tracer_provider,
    set_span_attributes,
)
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import (
    DocumentRecord,
    IngestionRunRecord,
    IngestJobRecordOrm,
)
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.raw_blob_store import RawBlobStorePort, build_raw_blob_store
from science_graphrag.storage.s3_artifact_store import build_artifact_store
from science_graphrag.utils.ingest_pipeline_log_heartbeat import pipeline_log_heartbeat_run
from science_graphrag.utils.ingest_vl_log_heartbeat import (
    VlLogHeartbeatState,
    maybe_log_vl_page_heartbeat,
    maybe_log_vl_parse_started,
)
from science_graphrag.utils.project_logging import get_logger

# Backward-compatible name for ``science_graphrag.ingestion.pipeline`` facade re-exports.
_strip_artifact_header = strip_ingest_artifact_header

logger = get_logger("ingestion.pipeline")

CORPUS_SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


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


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3), reraise=True)
def _openalex_lookup_with_retry(doi: str, mailto: str) -> dict[str, Any] | None:
    return fetch_work_by_doi(doi, mailto)


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


def discover_corpus_files(directory: Path) -> list[Path]:
    """Sorted list of ingestible files under directory (recursive)."""

    found: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in CORPUS_SUPPORTED_SUFFIXES:
            found.append(path)
    return found


def _default_progress_file() -> Path:
    return default_progress_file()


def _load_progress(path: Path) -> dict[str, str]:
    return load_progress(path)


def _append_progress(path: Path, entry: dict[str, Any]) -> None:
    append_progress(path, entry)


def _file_timeout(seconds: int):
    return file_timeout(seconds)


def _build_ingest_engine(settings: Settings):
    """Compatibility wrapper for tests monkeypatching get_engine/init_db."""
    engine = get_engine(settings.database_url)
    init_db(engine)
    return engine


def _run_dedup_audit(settings: Settings) -> None:
    """Compatibility wrapper for tests monkeypatching Neo4jGraphStore."""
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        violations = neo.find_work_dedup_violations()
    finally:
        neo.close()

    logger.info("--- Work dedup audit (Neo4j) ---")
    if not violations:
        logger.info(
            "OK: no duplicate Work clusters by doi / openalex_id / fingerprint / arxiv_id",
        )
        return
    logger.info("Found %s duplicate cluster(s):", len(violations))
    for item in violations:
        logger.info(
            "  [%s] key=%r work_ids=%s",
            item["kind"],
            item["dedup_key"],
            item["work_ids"],
        )


def _read_cached_markdown(
    settings: Settings,
    source_path: Path,
    *,
    document_id: str | None = None,
    artifact_store: ArtifactStorePort | None = None,
) -> tuple[str, str] | None:
    return read_cached_markdown(
        settings,
        source_path,
        document_id=document_id,
        artifact_store=artifact_store,
    )


def _markdown_from_path(
    path: Path,
    settings: Settings,
    *,
    document_id: str | None = None,
    on_vl_page_progress: Any | None = None,
    on_vl_batches_ready: Any | None = None,
) -> tuple[str, str, dict]:
    """Return (markdown, extraction_mode, vl_stats) where vl_stats may be empty dict."""
    suf = path.suffix.lower()
    if suf != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace"), "plain-text", {}

    if settings.reuse_cached_markdown:
        cached = _read_cached_markdown(settings, path, document_id=document_id)
        if cached is not None:
            return cached[0], cached[1], {}

    with chain_span(
        "ingest.parse_pdf.markdown",
        {"use_vl": settings.use_vl_for_pdf, "path": path.name},
    ):
        if settings.use_vl_for_pdf:
            try:
                processor = VLPDFProcessor(settings)
                markdown = processor.pdf_to_markdown(
                    path,
                    on_page_progress=on_vl_page_progress,
                    on_batches_ready=on_vl_batches_ready,
                )
                vl_stats = {
                    "vl_pages_total": processor.last_pages_total,
                    "vl_pages_processed": processor.last_pages_processed,
                    "vl_batch_count": processor.last_batch_count,
                }
                return markdown, "vl", vl_stats
            except Exception as exc:  # noqa: BLE001
                logger.warning("VL PDF failed for %s: %s; falling back to pypdf", path.name, exc)

        md = extract_text_from_pdf(path)
        if on_vl_page_progress is not None:
            try:
                on_vl_page_progress(1, 1)
            except Exception:  # noqa: BLE001
                pass
        return md, "pypdf-fallback", {}


_ARXIV_PREFIX_RE = re.compile(r"^arxiv:\s*", re.IGNORECASE)


def _normalize_arxiv_id(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    s = _ARXIV_PREFIX_RE.sub("", str(raw).strip())
    return s or None


def _normalized_title_for_fingerprint(title: str | None) -> str | None:
    if not title or not str(title).strip():
        return None
    return re.sub(r"\s+", " ", str(title).strip())


def _persist_reference_citation(
    neo: Neo4jGraphStore,
    citing_work_id: str,
    ref: ReferenceDraft,
    settings: Settings,
) -> None:
    """
    Create or merge a cited :Work and (:Work)-[:CITES]->(:Work) from a reference draft.
    Uses DOI (OpenAlex when possible), else arXiv id, else title+year fingerprint.
    """
    doi = normalize_doi(ref.doi)
    arxiv = _normalize_arxiv_id(ref.arxiv_id)

    if doi:
        try:
            oa = _openalex_lookup_with_retry(doi, settings.openalex_mailto)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAlex lookup failed for ref doi=%s: %s", doi, exc)
            oa = None
        if oa:
            cd = draft_from_openalex(oa)
            cid = _resolve_work_id(neo, cd)
            neo.upsert_minimal_work(
                cid,
                title=cd.title,
                publication_year=cd.publication_year,
                doi=cd.doi,
                arxiv_id=_normalize_arxiv_id(cd.arxiv_id),
                fingerprint=cd.fingerprint,
                openalex_id=cd.openalex_id,
                ingestion_confidence=cd.ingestion_confidence,
            )
        else:
            cid = neo.find_work_id_by_doi(doi)
            if not cid:
                cid = str(uuid.uuid4())
                neo.upsert_minimal_work(
                    cid,
                    title=ref.title,
                    publication_year=ref.year,
                    doi=doi,
                    arxiv_id=arxiv,
                    fingerprint=None,
                    openalex_id=None,
                    ingestion_confidence=0.25,
                )
        neo.merge_cites(citing_work_id, cid)
        return

    if arxiv:
        cid = neo.find_work_id_by_arxiv(arxiv) or str(uuid.uuid4())
        norm_title = _normalized_title_for_fingerprint(ref.title)
        fp = title_fingerprint(norm_title, ref.year) if norm_title else None
        neo.upsert_minimal_work(
            cid,
            title=norm_title,
            publication_year=ref.year,
            doi=None,
            arxiv_id=arxiv,
            fingerprint=fp,
            openalex_id=None,
            ingestion_confidence=0.35,
        )
        neo.merge_cites(citing_work_id, cid)
        return

    norm_title = _normalized_title_for_fingerprint(ref.title)
    if norm_title and ref.year is not None:
        fp = title_fingerprint(norm_title, ref.year)
        cid = neo.find_work_id_by_fingerprint(fp) or str(uuid.uuid4())
        neo.upsert_minimal_work(
            cid,
            title=norm_title,
            publication_year=ref.year,
            doi=None,
            arxiv_id=None,
            fingerprint=fp,
            openalex_id=None,
            ingestion_confidence=0.3,
        )
        neo.merge_cites(citing_work_id, cid)


def _resolve_work_id(neo: Neo4jGraphStore, draft: WorkDraft) -> str:
    if draft.doi:
        ex = neo.find_work_id_by_doi(draft.doi)
        if ex:
            return ex
    if draft.arxiv_id:
        ex = neo.find_work_id_by_arxiv(draft.arxiv_id)
        if ex:
            return ex
    if draft.fingerprint:
        ex = neo.find_work_id_by_fingerprint(draft.fingerprint)
        if ex:
            return ex
    return str(uuid.uuid4())


def _venue_id(name: str | None) -> str | None:
    if not name:
        return None
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "venue:" + name.strip().lower()))


def _institution_nodes_from_authorships(
    authorships,
    settings: Settings,
) -> list[tuple[str, str, str | None]]:
    """Compatibility wrapper delegating to canonical institution helper."""
    return institution_nodes_from_authorships(authorships, settings)


def _maybe_link_openalex_arxiv_version(
    neo: Neo4jGraphStore,
    work_id: str,
    draft: WorkDraft,
    oa_data: dict[str, Any] | None,
) -> None:
    """
    When OpenAlex exposes an arXiv id alongside a non-arXiv DOI, link preprint :Work.

    Edge: (journal Work)-[:RELATED_VERSION_OF]->(arXiv Work).
    """

    if not oa_data or not draft.doi:
        return
    doi_norm = normalize_doi(draft.doi)
    if not doi_norm:
        return
    if "arxiv" in doi_norm.lower() or doi_norm.startswith("10.48550/"):
        return
    arxiv_oa = arxiv_id_from_openalex_ids(oa_data)
    if not arxiv_oa:
        return
    existing = neo.find_work_id_by_arxiv(arxiv_oa)
    if existing == work_id:
        return
    arxiv_work_id = existing or str(uuid.uuid4())
    neo.upsert_minimal_work(
        arxiv_work_id,
        title=draft.normalized_title or draft.title,
        publication_year=draft.publication_year,
        doi=None,
        arxiv_id=arxiv_oa,
        fingerprint=None,
        openalex_id=None,
        ingestion_confidence=0.45,
    )
    neo.merge_related_version(work_id, arxiv_work_id)


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


def run_ingest_pipeline(ctx: IngestRunContext, source: IngestSource) -> IngestResult:
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
        return run_ingest_pipeline(ctx, IngestSource(path=path))
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


def run_ingest_batch_cli(
    directory: Path,
    *,
    continue_on_error: bool = False,
    settings: Settings | None = None,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    per_file_timeout_s: int = 900,
    resume: bool = False,
    progress_file: Path | None = None,
    embeddings_preflight: bool = False,
) -> list[dict[str, Any]]:
    """
    Ingest every ``.pdf`` / ``.md`` / ``.txt`` under ``directory`` (recursive).

    Prints a per-file summary and a post-hoc Neo4j :Work dedup audit
    (duplicate clusters by DOI, OpenAlex id, fingerprint, arXiv id).
    """

    init_tracer_provider()
    s = settings or get_settings()
    if embeddings_preflight:
        probe_embeddings(s)
    engine = _build_ingest_engine(s)
    progress_path = progress_file or _default_progress_file()
    rows = run_batch_ingest(
        directory,
        deps=BatchDeps(
            discover_corpus_files=discover_corpus_files,
            ingest_document=ingest_document,
            session_factory=session_factory,
        ),
        settings=s,
        engine=engine,
        progress_file=progress_path,
        continue_on_error=continue_on_error,
        skip_existing_sha=skip_existing_sha,
        force_new_document=force_new_document,
        per_file_timeout_s=per_file_timeout_s,
        resume=resume,
        duplicate_error_type=SkippedDuplicateIngestError,
    )

    _run_dedup_audit(s)
    return rows


def run_ingest_cli(
    path: Path,
    *,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    embeddings_preflight: bool = False,
) -> None:
    """CLI helper for single-file ingest."""
    init_tracer_provider()
    s = get_settings()
    if embeddings_preflight:
        probe_embeddings(s)
    engine = _build_ingest_engine(s)
    factory = session_factory(engine)
    with factory() as session:
        try:
            doc_id, work_id = ingest_document(
                path,
                settings=s,
                session=session,
                skip_existing_sha=skip_existing_sha,
                force_new_document=force_new_document,
            )
            logger.info("document_id=%s work_id=%s", doc_id, work_id)
        except SkippedDuplicateIngestError as dup:
            logger.info(
                "SKIP duplicate sha256=%s document_id=%s",
                dup.sha256,
                dup.document_id,
            )
