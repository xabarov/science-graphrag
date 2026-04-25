from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from tenacity import Retrying, retry, stop_after_attempt, wait_exponential

from science_graphrag.config import Settings, get_settings
from science_graphrag.domain.models import ReferenceDraft, WorkDraft
from science_graphrag.ingestion.chunking import (
    chunk_document_for_retrieval,
    dedupe_chunks_for_embedding,
)
from science_graphrag.ingestion.claims.extractor import extract_claims_llm
from science_graphrag.ingestion.dedup import normalize_doi, title_fingerprint
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
    strip_repeated_boilerplate,
)
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, try_sentence_transformer
from science_graphrag.ingestion.enrichment.openalex import (
    arxiv_id_from_openalex_ids,
    draft_from_openalex,
    fetch_work_by_doi,
)
from science_graphrag.ingestion.enrichment.ror import lookup_ror_id_optional
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_method_dataset
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.pdf import extract_text_from_pdf
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched
from science_graphrag.ingestion.vl_pdf import VLPDFProcessor
from science_graphrag.observability.phoenix_tracer import chain_span, init_tracer_provider
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore
from science_graphrag.utils.project_logging import configure_logging, get_logger

log = get_logger("ingestion.pipeline")

CORPUS_SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "document"


def _article_slug(path: Path) -> str:
    return _slug(path.stem)


def _canonical_article_rel(source_path: Path) -> Path:
    return Path("articles") / _article_slug(source_path) / "article.md"


def _canonical_diagnostics_rel(source_path: Path) -> Path:
    return Path("articles") / _article_slug(source_path) / "extraction_diagnostics.json"


def _strip_artifact_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("<!-- ") and "extraction_mode=" in lines[0]:
        lines = lines[2:] if len(lines) > 1 and lines[1] == "" else lines[1:]
    return "\n".join(lines)


def _read_cached_markdown(settings: Settings, source_path: Path) -> tuple[str, str] | None:
    artifact_root = Path(settings.artifact_root)
    canonical = artifact_root / _canonical_article_rel(source_path)
    candidates = [canonical]
    legacy = sorted(
        (artifact_root / "ingestion").glob(f"*/{_article_slug(source_path)}/article.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    candidates.extend(legacy)
    for candidate in candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        mode = "cached-markdown"
        mode_match = re.search(r"extraction_mode=([a-zA-Z0-9\\-]+)", first_line)
        if mode_match:
            mode = mode_match.group(1)
        log.info("Reusing cached article markdown for %s from %s", source_path.name, candidate)
        return _strip_artifact_header(text), mode
    return None


def _markdown_from_path(path: Path, settings: Settings) -> tuple[str, str]:
    suf = path.suffix.lower()
    if suf != ".pdf":
        return path.read_text(encoding="utf-8", errors="replace"), "plain-text"

    if settings.reuse_cached_markdown:
        cached = _read_cached_markdown(settings, path)
        if cached is not None:
            return cached

    with chain_span(
        "pdf_to_markdown",
        {"use_vl": settings.use_vl_for_pdf, "path": path.name},
    ):
        if settings.use_vl_for_pdf:
            try:
                markdown = VLPDFProcessor(settings).pdf_to_markdown(path)
                return markdown, "vl"
            except Exception as exc:  # noqa: BLE001
                log.warning("VL PDF failed for %s: %s; falling back to pypdf", path.name, exc)

        return extract_text_from_pdf(path), "pypdf-fallback"


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
    artifact_store = BlobStore(settings.artifact_root)
    slug = _article_slug(source_path)
    artifact_rel = Path("ingestion") / document_id / slug / "article.md"
    header = f"<!-- source={source_path.name} extraction_mode={extraction_mode} -->\n\n"
    body = header + markdown
    artifact_store.write_artifact(_canonical_article_rel(source_path), body)
    return artifact_store.write_artifact(artifact_rel, body)


def _write_extraction_diagnostics_json(
    *,
    settings: Settings,
    document_id: str,
    source_path: Path,
    diagnostics_json: str,
) -> Path:
    artifact_store = BlobStore(settings.artifact_root)
    slug = _article_slug(source_path)
    artifact_rel = Path("ingestion") / document_id / slug / "extraction_diagnostics.json"
    artifact_store.write_artifact(_canonical_diagnostics_rel(source_path), diagnostics_json)
    return artifact_store.write_artifact(artifact_rel, diagnostics_json)


def ingest_document(
    path: Path,
    *,
    settings: Settings | None = None,
    session: Session | None = None,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    stage_session_factory: Any | None = None,
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
    with chain_span(
        "ingest_document",
        {
            "document.id": doc_id,
            "document.source_name": path.name,
            "document.sha256": sha,
            "document.reused_id": reused_doc,
            "source": str(path.resolve()),
        },
    ):
        with stage(job_id, IngestStage.PARSE_PDF, session_factory=stage_session_factory) as st:
            markdown_text, extraction_mode = _markdown_from_path(path, settings)
            st.metric("source_suffix", path.suffix.lower())
            st.metric("extraction_mode", extraction_mode)
        _artifact_path = _write_markdown_artifact(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            markdown=markdown_text,
            extraction_mode=extraction_mode,
        )
        normalized = strip_repeated_boilerplate(normalize_text(markdown_text))
        blob_store.write_text("extracted.txt", normalized)

        front = front_matter_slice(
            normalized,
            max_chars=settings.front_matter_max_chars,
        )
        ref_scope = build_references_scope_text(
            normalized,
            max_chars=settings.references_scope_max_chars,
        )

        with stage(job_id, IngestStage.EXTRACT_META, session_factory=stage_session_factory) as st:
            with chain_span(
                "metadata_and_references_extraction",
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
        _write_extraction_diagnostics_json(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            diagnostics_json=ext_diag.to_json(),
        )

        oa_raw: dict[str, Any] | None = None
        with stage(
            job_id, IngestStage.ENRICH_OPENALEX, session_factory=stage_session_factory
        ) as st:
            with chain_span("openalex_enrichment"):
                if draft.doi:
                    try:
                        oa = _openalex_lookup_with_retry(draft.doi, settings.openalex_mailto)
                        if oa:
                            oa_raw = oa
                            enriched = draft_from_openalex(oa)
                            draft = merge_draft_prefer_enriched(draft, enriched)
                    except Exception as exc:  # noqa: BLE001
                        log.warning("OpenAlex enrichment failed for doi=%s: %s", draft.doi, exc)
            st.metric("has_doi", int(bool(draft.doi)))
            st.metric("enriched", int(bool(oa_raw)))

        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            with chain_span("neo4j_graph_persistence"):
                _retry_call(neo.ensure_schema)
                work_id = _resolve_work_id(neo, draft)
                vid = _venue_id(draft.venue_name)
                with stage(
                    job_id, IngestStage.ENRICH_ROR, session_factory=stage_session_factory
                ) as st:
                    inst_nodes = _institution_nodes_from_authorships(authorships, settings)
                    st.metric("institutions", len(inst_nodes))

                with stage(
                    job_id, IngestStage.WRITE_GRAPH, session_factory=stage_session_factory
                ) as st:
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
                        "semantic_method_dataset",
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

                with stage(
                    job_id, IngestStage.RESOLVE_REFERENCES, session_factory=stage_session_factory
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

            with stage(job_id, IngestStage.CHUNK, session_factory=stage_session_factory) as st:
                doc_chunks = dedupe_chunks_for_embedding(
                    chunk_document_for_retrieval(
                        normalized,
                        target_tokens=settings.chunk_target_tokens,
                        overlap_tokens=settings.chunk_overlap_tokens,
                    ),
                )
                st.metric("chunks", len(doc_chunks))
            claim_rows: list[Any] = []
            if settings.claims_extraction_enabled:
                chunk_dicts = [
                    {
                        "text": c.text,
                        "chunk_fingerprint": c.chunk_fingerprint,
                        "section_path": c.section_path,
                    }
                    for c in doc_chunks
                ]
                with stage(
                    job_id, IngestStage.EXTRACT_CLAIMS, session_factory=stage_session_factory
                ) as st:
                    with chain_span(
                        "claims_extraction",
                        {"document.id": doc_id, "work.id": work_id, "chunks": len(chunk_dicts)},
                    ):
                        claim_rows = extract_claims_llm(
                            chunk_dicts,
                            work_id,
                            settings,
                            force_benchmark=False,
                        )
                    st.metric("claims", len(claim_rows))
                _retry_call(neo.detach_delete_claims_for_work, work_id)
                _retry_call(neo.upsert_claims_with_evidence, work_id, claim_rows)

            with stage(job_id, IngestStage.EMBED, session_factory=stage_session_factory) as st:
                embedder = (
                    try_sentence_transformer(settings.embedding_model)
                    if settings.embedding_model
                    else HashEmbeddingProvider()
                )
                chunk_texts = [c.text for c in doc_chunks]
                vectors = embedder.embed(chunk_texts)
                first_author = ""
                if authorships:
                    ordered_auth = sorted(authorships, key=lambda x: x.author_position or 0)
                    first_author = (ordered_auth[0].author_raw_name or "").strip()
                summary_text = f"{draft.title or ''}\n{draft.abstract or ''}\n{first_author}"[:8000]
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
                    embedding_model=settings.embedding_model or "hash-deterministic",
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
                removed = _retry_call(q.delete_points_by_document_id, document_id=doc_id)
                if removed and reused_doc:
                    log.info(
                        "qdrant removed %s point(s) before re-ingest document_id=%s",
                        removed,
                        doc_id,
                    )
                with chain_span(
                    "qdrant_vector_upsert",
                    {
                        "chunks": len(doc_chunks),
                        "embedding": settings.embedding_model or "hash",
                    },
                ):
                    _retry_call(
                        q.upsert_document_chunks,
                        work_id=work_id,
                        document_id=doc_id,
                        document_chunks=doc_chunks,
                        vectors=vectors,
                        embedding_model=settings.embedding_model or "hash-deterministic",
                        workspace_ids=ingest_workspace_ids or [],
                    )
                if settings.claims_extraction_enabled and claim_rows:
                    with chain_span(
                        "qdrant_claims_upsert",
                        {
                            "claims": len(claim_rows),
                            "embedding": settings.embedding_model or "hash",
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
                            embedding_model=settings.embedding_model or "hash-deterministic",
                        )
                st.metric("chunks", len(doc_chunks))
                st.metric("embedding_dim", embedder.dim)
        finally:
            neo.close()

        if session is not None:
            now = datetime.now(UTC)
            mime = f"application/{path.suffix.lower().lstrip('.') or 'octet-stream'}"
            if reused_doc:
                existing = session.get(DocumentRecord, doc_id)
                if existing is not None:
                    existing.source_path = str(path.resolve())
                    existing.mime_type = mime
                    existing.sha256 = sha
                    existing.work_id = work_id
            else:
                session.add(
                    DocumentRecord(
                        id=doc_id,
                        sha256=sha,
                        source_path=str(path.resolve()),
                        mime_type=mime,
                        work_id=work_id,
                    ),
                )
            session.add(
                IngestionRunRecord(
                    document_id=doc_id,
                    status="completed",
                    finished_at=now,
                ),
            )

        return doc_id, work_id


def run_ingest_batch_cli(
    directory: Path,
    *,
    continue_on_error: bool = False,
    settings: Settings | None = None,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
) -> list[dict[str, Any]]:
    """
    Ingest every ``.pdf`` / ``.md`` / ``.txt`` under ``directory`` (recursive).

    Prints a per-file summary and a post-hoc Neo4j :Work dedup audit
    (duplicate clusters by DOI, OpenAlex id, fingerprint, arXiv id).
    """

    configure_logging()
    init_tracer_provider()
    s = settings or get_settings()
    engine = get_engine(s.database_url)
    init_db(engine)
    factory = session_factory(engine)
    paths = discover_corpus_files(directory)
    if not paths:
        log.warning("No ingestible files under %s", directory)
        print("No .pdf/.md/.txt files found.")
        return []

    rows: list[dict[str, Any]] = []
    for path in paths:
        try:
            with factory() as db_session:
                with db_session.begin():
                    doc_id, work_id = ingest_document(
                        path,
                        settings=s,
                        session=db_session,
                        skip_existing_sha=skip_existing_sha,
                        force_new_document=force_new_document,
                    )
            rows.append(
                {
                    "path": str(path.resolve()),
                    "document_id": doc_id,
                    "work_id": work_id,
                    "error": None,
                    "skipped_duplicate": False,
                },
            )
            print(f"OK path={path} document_id={doc_id} work_id={work_id}")
        except SkippedDuplicateIngestError as dup:
            rows.append(
                {
                    "path": str(path.resolve()),
                    "document_id": dup.document_id,
                    "work_id": None,
                    "error": None,
                    "skipped_duplicate": True,
                },
            )
            print(f"SKIP duplicate-sha path={path} document_id={dup.document_id}")
        except Exception as exc:  # noqa: BLE001
            log.exception("Ingest failed for %s", path)
            rows.append(
                {
                    "path": str(path.resolve()),
                    "document_id": None,
                    "work_id": None,
                    "error": str(exc),
                    "skipped_duplicate": False,
                },
            )
            print(f"FAIL path={path} error={exc}")
            if not continue_on_error:
                break

    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        violations = neo.find_work_dedup_violations()
    finally:
        neo.close()

    print("\n--- Work dedup audit (Neo4j) ---")
    if not violations:
        print("OK: no duplicate Work clusters by doi / openalex_id / fingerprint / arxiv_id")
    else:
        print(f"Found {len(violations)} duplicate cluster(s):")
        for item in violations:
            print(
                f"  [{item['kind']}] key={item['dedup_key']!r} " f"work_ids={item['work_ids']}",
            )
    return rows


def run_ingest_cli(
    path: Path,
    *,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
) -> None:
    configure_logging()
    init_tracer_provider()
    s = get_settings()
    engine = get_engine(s.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        try:
            with session.begin():
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
