from __future__ import annotations

import json
import re
import signal
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opentelemetry import trace as trace_api
from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import Retrying, retry, stop_after_attempt, wait_exponential

from science_graphrag.config import Settings, get_settings
from science_graphrag.domain.models import ReferenceDraft, WorkDraft
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.artifact_layout import (
    canonical_article_md_rel,
    canonical_normalized_md_rel,
    strip_ingest_artifact_header,
)
from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval_from_settings,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
    strip_repeated_boilerplate,
)
from science_graphrag.ingestion.enrichment.openalex import (
    arxiv_id_from_openalex_ids,
    draft_from_openalex,
    fetch_work_by_doi,
)
from science_graphrag.ingestion.enrichment.ror import lookup_ror_id_optional
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.ingestion.markdown_fence import strip_whole_document_markdown_fence

# Backward-compatible name for ``science_graphrag.ingestion.pipeline`` facade re-exports.
_strip_artifact_header = strip_ingest_artifact_header
from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.dedup.entity_ingest_conflict_check import (
    enqueue_entity_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.dedup.ingest_conflict_check import (
    enqueue_author_near_duplicate_conflicts_on_ingest,
    enqueue_work_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.embeddings.errors import EmbeddingCallError, EmbeddingNonRetryableHttpError
from science_graphrag.ingestion.checkpoint import (
    default_checkpoint,
    mark_stage_completed,
    mark_stage_failed,
    parse_checkpoint,
    serialize_checkpoint,
)
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.stage_context import (
    IngestRunContext,
    IngestStage,
    StageHandle,
    build_ingest_run_context,
    stage,
)
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched
from science_graphrag.ingestion.vl_pdf import VLPDFProcessor
from science_graphrag.observability.phoenix_tracer import (
    OpenInferenceAttributes,
    SpanAttributes,
    chain_span,
    embeddings_span,
    init_tracer_provider,
    llm_span,
    set_span_attributes,
)
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import (
    DocumentRecord,
    IngestionRunRecord,
    IngestJobRecordOrm,
)
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore
from science_graphrag.utils.project_logging import configure_logging, get_logger

log = get_logger("ingestion.pipeline")

CORPUS_SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


@dataclass(slots=True)
class IngestSource:
    path: Path


@dataclass(slots=True)
class IngestResult:
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
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return Path("eval/results") / f"ingest-progress-{run_id}.jsonl"


def _load_progress(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        raw_path = payload.get("path")
        status = payload.get("status")
        if not isinstance(raw_path, str) or not isinstance(status, str):
            continue
        rows[raw_path] = status
    return rows


def _append_progress(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(existing + line, encoding="utf-8")
    tmp.replace(path)


@contextmanager
def _file_timeout(seconds: int):
    if seconds <= 0:
        yield
        return
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handler(_sig, _frame):
        raise TimeoutError(f"ingest_document exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "document"


def _article_slug(path: Path) -> str:
    return _slug(path.stem)


def _canonical_article_rel(source_path: Path) -> Path:
    return Path("articles") / _article_slug(source_path) / "article.md"


def _canonical_diagnostics_rel(source_path: Path) -> Path:
    return Path("articles") / _article_slug(source_path) / "extraction_diagnostics.json"


def _read_cached_markdown(
    settings: Settings, source_path: Path, *, document_id: str | None = None
) -> tuple[str, str] | None:
    store = LocalFilesystemArtifactStore(Path(settings.artifact_root))
    candidates: list[Path] = []
    if document_id:
        candidates.append(store.absolute(canonical_article_md_rel(document_id)))
        candidates.append(store.absolute(canonical_normalized_md_rel(document_id)))
    canonical = store.absolute(_canonical_article_rel(source_path))
    candidates.append(canonical)
    legacy = sorted(
        store.glob_under(f"ingestion/*/{_article_slug(source_path)}/article.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    candidates.extend(legacy)
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        mode = "cached-markdown"
        mode_match = re.search(r"extraction_mode=([a-zA-Z0-9\\-]+)", first_line)
        if mode_match:
            mode = mode_match.group(1)
        elif candidate.name == "normalized.md":
            mode = "cached-normalized"
        log.info("Reusing cached article markdown for %s from %s", source_path.name, candidate)
        return strip_ingest_artifact_header(text), mode
    return None


def _markdown_from_path(
    path: Path, settings: Settings, *, document_id: str | None = None
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
                markdown = processor.pdf_to_markdown(path)
                vl_stats = {
                    "vl_pages_total": processor.last_pages_total,
                    "vl_pages_processed": processor.last_pages_processed,
                    "vl_batch_count": processor.last_batch_count,
                }
                return markdown, "vl", vl_stats
            except Exception as exc:  # noqa: BLE001
                log.warning("VL PDF failed for %s: %s; falling back to pypdf", path.name, exc)

        return extract_text_from_pdf(path), "pypdf-fallback", {}


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
            log.warning("OpenAlex lookup failed for ref doi=%s: %s", doi, exc)
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
    nodes: list[tuple[str, str, str | None]] = []
    for authorship in authorships:
        affiliation = next((value for value in authorship.raw_affiliations if value.strip()), None)
        if not affiliation:
            continue
        clean = affiliation.strip()
        inst_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "institution:" + clean.lower()))
        ror_id: str | None = None
        if settings.ror_lookup_enabled:
            ror_id = lookup_ror_id_optional(clean, settings.openalex_mailto)
        nodes.append((inst_id, clean, ror_id))
    return nodes


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
) -> Path:
    """Write canonical ``ingestion/{document_id}/article.md`` plus legacy slug paths."""
    artifact_store = LocalFilesystemArtifactStore(Path(settings.artifact_root))
    slug = _article_slug(source_path)
    legacy_rel = Path("ingestion") / document_id / slug / "article.md"
    header = f"<!-- source={source_path.name} extraction_mode={extraction_mode} -->\n\n"
    body = header + markdown
    artifact_store.write_text(canonical_article_md_rel(document_id), body)
    artifact_store.write_text(_canonical_article_rel(source_path), body)
    return artifact_store.write_text(legacy_rel, body)


def _write_extraction_diagnostics_json(
    *,
    settings: Settings,
    document_id: str,
    source_path: Path,
    diagnostics_json: str,
) -> Path:
    artifact_store = LocalFilesystemArtifactStore(Path(settings.artifact_root))
    slug = _article_slug(source_path)
    artifact_rel = Path("ingestion") / document_id / slug / "extraction_diagnostics.json"
    artifact_store.write_text(_canonical_diagnostics_rel(source_path), diagnostics_json)
    return artifact_store.write_text(artifact_rel, diagnostics_json)


def run_ingest_pipeline(ctx: IngestRunContext, source: IngestSource) -> IngestResult:
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
) -> IngestResult:
    ctx = build_ingest_run_context(
        settings=settings,
        source_path=path,
        session=session,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
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
) -> IngestResult:
    return run_ingest_from_file(
        path,
        settings=settings,
        session=session,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        parent_job_id=parent_job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
    )


def _sql_commit_if_session(session: Session | None) -> None:
    """Commit SQL work at orchestration boundaries (embed vs graph split)."""
    if session is not None:
        session.commit()


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
    st: StageHandle,
    reused_doc: bool,
) -> None:
    """Vectorize chunks + work summary and upsert Qdrant (after Neo4j is closed)."""

    embedder = resolve_embedder(settings)
    chunk_texts = [c.text for c in doc_chunks]
    embedding_model = resolve_embedding_model_label(settings)
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
    _retry_call(
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
    removed = _retry_call(q.delete_points_by_document_id, document_id=document_id)
    if removed and reused_doc:
        log.info(
            "qdrant removed %s point(s) before re-ingest document_id=%s",
            removed,
            document_id,
        )
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
        _retry_call(
            q.upsert_document_chunks,
            work_id=work_id,
            document_id=document_id,
            document_chunks=doc_chunks,
            vectors=vectors,
            embedding_model=embedding_model,
            workspace_ids=ingest_workspace_ids or [],
        )
    if settings.claims_extraction_enabled and claim_rows:
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
            _retry_call(qc.delete_points_by_work_id, work_id=work_id)
            _retry_call(
                qc.upsert_claims,
                work_id=work_id,
                claims=claim_rows,
                embedder=embedder,
                embedding_model=embedding_model,
            )
    st.metric("chunks", len(doc_chunks))
    st.metric("embedding_dim", embedder.dim)


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
) -> tuple[str, str]:
    """
    Ingest one PDF or text file. Returns (document_id, work_id).

    With a SQL ``session``, the same file bytes (``sha256``) reuse the existing ``document_id``
    by default, Qdrant rows for that id are replaced, and Postgres metadata is updated.
    Use ``skip_existing_sha`` to no-op when the hash exists; ``force_new_document`` for a new row
    every time (no SQL dedup — e.g. benchmarks with ``session is None``).
    """
    configure_logging()
    settings = settings or get_settings()
    blob_store = BlobStore(settings.blob_root)
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
    workspace_id = (ingest_workspace_ids or [None])[0]
    root_attrs: dict[str, Any] = {
        "document.id": doc_id,
        "document.source_name": path.name,
        "document.sha256": sha,
        "document.reused_id": reused_doc,
        "source": str(path.resolve()),
        "metadata.source_name": path.name,
        "metadata.extraction_llm_model": settings.extraction_llm_model,
        "metadata.embedding_model": resolve_embedding_model_label(settings),
        "metadata.vl_model": settings.vl_model,
    }
    if job_id:
        root_attrs[OpenInferenceAttributes.SESSION_ID] = str(job_id)
        root_attrs["metadata.job_id"] = str(job_id)
    if parent_job_id:
        root_attrs["metadata.parent_job_id"] = str(parent_job_id)
    if workspace_id:
        root_attrs[OpenInferenceAttributes.USER_ID] = str(workspace_id)
        root_attrs["metadata.workspace_id"] = str(workspace_id)
    with chain_span("ingest_document", root_attrs):
        ckpt: dict[str, Any] = default_checkpoint()
        if session is not None and reused_doc:
            prev_doc = session.get(DocumentRecord, doc_id)
            if prev_doc is not None and prev_doc.ingest_checkpoint_json:
                ckpt = parse_checkpoint(prev_doc.ingest_checkpoint_json)
        if session is not None and job_id:
            trace_ctx = trace_api.get_current_span().get_span_context()
            if trace_ctx.trace_id:
                trace_id = format(trace_ctx.trace_id, "032x")
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if row is not None and not row.phoenix_trace_id:
                    row.phoenix_trace_id = trace_id
        with stage(
            job_id,
            IngestStage.PARSE_PDF,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
        ) as st:
            markdown_text, extraction_mode, vl_stats = _markdown_from_path(
                path, settings, document_id=doc_id
            )
            set_span_attributes({"metadata.extraction_mode": extraction_mode})
            st.metric("source_suffix", path.suffix.lower())
            st.metric("extraction_mode", extraction_mode)
        _artifact_path = _write_markdown_artifact(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            markdown=markdown_text,
            extraction_mode=extraction_mode,
        )
        normalized = strip_repeated_boilerplate(
            normalize_text(strip_whole_document_markdown_fence(markdown_text))
        )
        LocalFilesystemArtifactStore(Path(settings.artifact_root)).write_text(
            canonical_normalized_md_rel(doc_id),
            normalized,
        )

        front = front_matter_slice(
            normalized,
            max_chars=settings.front_matter_max_chars,
        )
        ref_scope = build_references_scope_text(
            normalized,
            max_chars=settings.references_scope_max_chars,
        )

        with stage(
            job_id,
            IngestStage.EXTRACT_META,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
        ) as st:
            with chain_span(
                "ingest.extract_meta.metadata_and_refs",
                {
                    "document.id": doc_id,
                    "document.source_name": path.name,
                },
            ):
                draft, authorships, references, ext_diag = extract_stages_llm_first(
                    normalized,
                    settings,
                    markdown_source=extraction_mode,
                    document_id=doc_id,
                    source_name=path.name,
                    front_matter_text=front.text,
                    references_scope_text=ref_scope,
                )
            st.metric("references", len(references))
            st.metric("authorships", len(authorships))
        if vl_stats:
            ext_diag.vl_pages_total = vl_stats.get("vl_pages_total")
            ext_diag.vl_pages_processed = vl_stats.get("vl_pages_processed")
            ext_diag.vl_batch_count = vl_stats.get("vl_batch_count")
        _write_extraction_diagnostics_json(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            diagnostics_json=ext_diag.to_json(),
        )

        oa_raw: dict[str, Any] | None = None
        with stage(
            job_id,
            IngestStage.ENRICH_OPENALEX,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
        ) as st:
            with chain_span("ingest.enrich_openalex.lookup"):
                SpanAttributes.set_input({"doi": draft.doi})
                if draft.doi:
                    openalex_url = f"https://api.openalex.org/works/doi:{draft.doi}"
                    set_span_attributes(
                        {
                            "http.request.method": "GET",
                            "http.url": openalex_url,
                            "openalex.doi": draft.doi,
                            "retry.attempts": 3,
                        }
                    )
                    try:
                        oa = _openalex_lookup_with_retry(draft.doi, settings.openalex_mailto)
                        if oa:
                            oa_raw = oa
                            enriched = draft_from_openalex(oa)
                            draft = merge_draft_prefer_enriched(draft, enriched)
                            SpanAttributes.set_output(
                                {
                                    "openalex_id": oa.get("id"),
                                    "title": (oa.get("display_name") or "")[:300],
                                }
                            )
                            set_span_attributes({"openalex.found": True})
                        else:
                            set_span_attributes({"openalex.found": False})
                    except Exception as exc:  # noqa: BLE001
                        set_span_attributes({"openalex.found": False})
                        log.warning("OpenAlex enrichment failed for doi=%s: %s", draft.doi, exc)
            st.metric("has_doi", int(bool(draft.doi)))
            st.metric("enriched", int(bool(oa_raw)))

        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            _retry_call(neo.ensure_schema)
            work_id = _resolve_work_id(neo, draft)
            vid = _venue_id(draft.venue_name)
            with stage(
                job_id,
                IngestStage.ENRICH_ROR,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
            ) as st:
                inst_nodes = _institution_nodes_from_authorships(authorships, settings)
                st.metric("institutions", len(inst_nodes))

            with stage(
                job_id,
                IngestStage.WRITE_GRAPH,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
            ) as st:
                if session is not None:
                    try:
                        n_dedup = enqueue_work_near_duplicate_conflicts_on_ingest(
                            settings=settings,
                            session=session,
                            neo=neo,
                            workspace_id=workspace_id,
                            new_work_id=work_id,
                            draft=draft,
                            authorships=authorships,
                        )
                        st.metric("ingest_dedup_conflicts_enqueued", n_dedup)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("ingest_dedup_conflict_check_failed: %s", exc)
                with chain_span(
                    "ingest.write_graph.upsert_work_layer1",
                    {"db.system": "neo4j", "db.operation": "merge", "writes.count": 1},
                ):
                    _retry_call(
                        neo.upsert_work_layer1,
                        work_id,
                        draft,
                        authorships,
                        venue_id=vid,
                        institution_nodes=inst_nodes,
                    )
                st.metric("authorships", len(authorships))

                with chain_span(
                    "ingest.write_graph.semantic",
                    {"document.id": doc_id, "work.id": work_id},
                ):
                    semantic = extract_semantic_method_dataset(
                        normalized,
                        settings,
                        document_id=doc_id,
                    )
                    _retry_call(
                        neo.sync_work_semantic_layer,
                        work_id,
                        semantic,
                        confidence_threshold=settings.semantic_graph_confidence_threshold,
                    )
                st.metric("semantic_claims", len(getattr(semantic, "claims", []) or []))

                if session is not None:
                    try:
                        n_author_dedup = enqueue_author_near_duplicate_conflicts_on_ingest(
                            settings=settings,
                            session=session,
                            neo=neo,
                            workspace_id=workspace_id,
                            new_work_id=work_id,
                        )
                        st.metric("ingest_author_dedup_conflicts_enqueued", n_author_dedup)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("ingest_author_dedup_conflict_check_failed: %s", exc)
                    try:
                        ent_dedup = enqueue_entity_near_duplicate_conflicts_on_ingest(
                            session=session,
                            neo=neo,
                            workspace_id=workspace_id,
                            new_work_id=work_id,
                            settings=settings,
                        )
                        st.metric(
                            "ingest_entity_dedup_conflicts_enqueued",
                            int(
                                sum(
                                    int(ent_dedup.get(k, 0))
                                    for k in ("institution", "venue", "method", "dataset")
                                )
                            ),
                        )
                        st.metric(
                            "ingest_method_dedup_auto_merged",
                            int(ent_dedup.get("method_ingest_auto_merged", 0)),
                        )
                        st.metric(
                            "ingest_method_dedup_llm_merged",
                            int(ent_dedup.get("method_ingest_llm_merged", 0)),
                        )
                    except Exception as exc:  # noqa: BLE001
                        log.warning("ingest_entity_dedup_conflict_check_failed: %s", exc)

            with stage(
                job_id,
                IngestStage.RESOLVE_REFERENCES,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
            ) as st:
                linked_refs = 0
                for ref in references:
                    if not (
                        normalize_doi(ref.doi)
                        or _normalize_arxiv_id(ref.arxiv_id)
                        or (
                            _normalized_title_for_fingerprint(ref.title) is not None
                            and ref.year is not None
                        )
                    ):
                        continue
                    _retry_call(_persist_reference_citation, neo, work_id, ref, settings)
                    linked_refs += 1
                st.metric("references_total", len(references))
                st.metric("references_linked", linked_refs)

            _retry_call(_maybe_link_openalex_arxiv_version, neo, work_id, draft, oa_raw)

            with stage(
                job_id,
                IngestStage.CHUNK,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
            ) as st:
                doc_chunks = dedupe_chunks_for_embedding(
                    chunk_document_for_retrieval_from_settings(normalized, settings),
                )
                st.metric("chunks", len(doc_chunks))
            claim_rows: list[Any] = []
            with stage(
                job_id,
                IngestStage.EXTRACT_CLAIMS,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
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
                        _retry_call(neo.detach_delete_claims_for_work, work_id)
                        _retry_call(neo.upsert_claims_with_evidence, work_id, claim_rows)
                else:
                    st.metric("claims_extraction_enabled", 0)

        finally:
            neo.close()

        mark_stage_completed(ckpt, IngestStage.EXTRACT_CLAIMS)

        ingest_run: IngestionRunRecord | None = None
        if session is not None:
            now = datetime.now(UTC)
            mime = f"application/{path.suffix.lower().lstrip('.') or 'octet-stream'}"
            serialized_ckpt = serialize_checkpoint(ckpt)
            if reused_doc:
                existing = session.get(DocumentRecord, doc_id)
                if existing is not None:
                    existing.source_path = str(path.resolve())
                    existing.mime_type = mime
                    existing.sha256 = sha
                    existing.work_id = work_id
                    existing.ingest_checkpoint_json = serialized_ckpt
            else:
                session.add(
                    DocumentRecord(
                        id=doc_id,
                        sha256=sha,
                        source_path=str(path.resolve()),
                        mime_type=mime,
                        work_id=work_id,
                        ingest_checkpoint_json=serialized_ckpt,
                    ),
                )
            ingest_run = IngestionRunRecord(
                document_id=doc_id,
                status="running",
                started_at=now,
                finished_at=None,
            )
            session.add(ingest_run)
            session.flush()
            _sql_commit_if_session(session)

        try:
            with stage(
                job_id,
                IngestStage.EMBED,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
            ) as st:
                run_ingest_embed_qdrant_phase(
                    settings=settings,
                    document_id=doc_id,
                    work_id=work_id,
                    doc_chunks=doc_chunks,
                    claim_rows=claim_rows,
                    authorships=authorships,
                    draft=draft,
                    ingest_workspace_ids=ingest_workspace_ids,
                    st=st,
                    reused_doc=reused_doc,
                )
        except Exception as embed_exc:
            if session is not None:
                retryable = True
                if isinstance(embed_exc, EmbeddingNonRetryableHttpError):
                    retryable = False
                elif isinstance(embed_exc, EmbeddingCallError):
                    retryable = embed_exc.retryable
                mark_stage_failed(
                    ckpt,
                    IngestStage.EMBED,
                    error=str(embed_exc),
                    retryable=retryable,
                )
                row = session.get(DocumentRecord, doc_id)
                if row is not None:
                    row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
                if ingest_run is not None:
                    ingest_run.status = "failed_retryable" if retryable else "failed_terminal"
                    ingest_run.error_message = str(embed_exc)[:8000]
                    ingest_run.finished_at = datetime.now(UTC)
                _sql_commit_if_session(session)
            raise
        mark_stage_completed(ckpt, IngestStage.EMBED)
        if session is not None:
            finished = datetime.now(UTC)
            if ingest_run is not None:
                ingest_run.status = "completed"
                ingest_run.finished_at = finished
            row = session.get(DocumentRecord, doc_id)
            if row is not None:
                row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
            _sql_commit_if_session(session)

        return doc_id, work_id


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

    configure_logging()
    init_tracer_provider()
    s = settings or get_settings()
    if embeddings_preflight:
        from science_graphrag.embeddings.preflight import probe_embeddings

        probe_embeddings(s)
    engine = get_engine(s.database_url)
    init_db(engine)
    factory = session_factory(engine)
    paths = discover_corpus_files(directory)
    if not paths:
        log.warning("No ingestible files under %s", directory)
        print("No .pdf/.md/.txt files found.", flush=True)
        return []

    progress_path = progress_file or _default_progress_file()
    progress_by_path = _load_progress(progress_path) if resume else {}

    rows: list[dict[str, Any]] = []
    for path in paths:
        resolved_path = str(path.resolve())
        if resume and progress_by_path.get(resolved_path) == "ok":
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": None,
                    "skipped_duplicate": False,
                    "status": "skip",
                },
            )
            print(f"SKIP resumed=ok path={path}", flush=True)
            continue

        started_at = datetime.now(UTC)
        try:
            with factory() as db_session:
                with _file_timeout(per_file_timeout_s):
                    doc_id, work_id = ingest_document(
                        path,
                        settings=s,
                        session=db_session,
                        skip_existing_sha=skip_existing_sha,
                        force_new_document=force_new_document,
                    )
            finished_at = datetime.now(UTC)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": doc_id,
                    "work_id": work_id,
                    "error": None,
                    "skipped_duplicate": False,
                    "status": "ok",
                },
            )
            _append_progress(
                progress_path,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "ok",
                    "document_id": doc_id,
                    "work_id": work_id,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": None,
                },
            )
            print(f"OK path={path} document_id={doc_id} work_id={work_id}", flush=True)
        except TimeoutError as exc:
            log.exception("Ingest timeout for %s", path)
            finished_at = datetime.now(UTC)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": str(exc),
                    "skipped_duplicate": False,
                    "status": "timeout",
                },
            )
            _append_progress(
                progress_path,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "timeout",
                    "document_id": None,
                    "work_id": None,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": str(exc),
                },
            )
            print(f"FAIL_TIMEOUT path={path} error={exc}", flush=True)
            if not continue_on_error:
                break
        except SkippedDuplicateIngestError as dup:
            finished_at = datetime.now(UTC)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": dup.document_id,
                    "work_id": None,
                    "error": None,
                    "skipped_duplicate": True,
                    "status": "skip",
                },
            )
            _append_progress(
                progress_path,
                {
                    "path": resolved_path,
                    "sha256": dup.sha256,
                    "status": "skip",
                    "document_id": dup.document_id,
                    "work_id": None,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": None,
                },
            )
            print(f"SKIP duplicate-sha path={path} document_id={dup.document_id}", flush=True)
        except Exception as exc:  # noqa: BLE001
            log.exception("Ingest failed for %s", path)
            finished_at = datetime.now(UTC)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": str(exc),
                    "skipped_duplicate": False,
                    "status": "fail",
                },
            )
            _append_progress(
                progress_path,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "fail",
                    "document_id": None,
                    "work_id": None,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": str(exc),
                },
            )
            print(f"FAIL path={path} error={exc}", flush=True)
            if not continue_on_error:
                break

    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        violations = neo.find_work_dedup_violations()
    finally:
        neo.close()

    print("\n--- Work dedup audit (Neo4j) ---", flush=True)
    if not violations:
        print(
            "OK: no duplicate Work clusters by doi / openalex_id / fingerprint / arxiv_id",
            flush=True,
        )
    else:
        print(f"Found {len(violations)} duplicate cluster(s):", flush=True)
        for item in violations:
            print(
                f"  [{item['kind']}] key={item['dedup_key']!r} " f"work_ids={item['work_ids']}",
                flush=True,
            )
    return rows


def run_ingest_cli(
    path: Path,
    *,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    embeddings_preflight: bool = False,
) -> None:
    configure_logging()
    init_tracer_provider()
    s = get_settings()
    if embeddings_preflight:
        from science_graphrag.embeddings.preflight import probe_embeddings

        probe_embeddings(s)
    engine = get_engine(s.database_url)
    init_db(engine)
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
            print(f"document_id={doc_id} work_id={work_id}")
        except SkippedDuplicateIngestError as dup:
            print(f"SKIP duplicate sha256={dup.sha256} document_id={dup.document_id}")
