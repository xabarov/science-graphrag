"""Resume late-stage ingest stages for documents with persisted artifacts."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session
from tenacity import Retrying, stop_after_attempt, wait_exponential

from science_graphrag.domain.models import WorkDraft
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.embeddings.errors import EmbeddingCallError, EmbeddingNonRetryableHttpError
from science_graphrag.ingestion.artifact_layout import canonical_normalized_md_rel
from science_graphrag.ingestion.checkpoint import (
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
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
    strip_repeated_boilerplate,
)
from science_graphrag.ingestion.embed_phase import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.enrichment.openalex import draft_from_openalex
from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first
from science_graphrag.ingestion.markdown_fence import strip_whole_document_markdown_fence
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.reference_citations import (
    maybe_link_openalex_arxiv_version,
    normalize_arxiv_id,
    normalized_title_for_fingerprint,
    openalex_lookup_with_retry,
    persist_reference_citation,
)
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched
from science_graphrag.storage.models_orm import DocumentRecord, IngestionRunRecord
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.s3_artifact_store import build_artifact_store
from science_graphrag.utils.project_logging import get_logger

if TYPE_CHECKING:
    from science_graphrag.config import Settings

log = get_logger("ingestion.resume")


def _resume_failure_retryable(exc: BaseException) -> bool:
    """Heuristic for ingest-resume failures: persist retry hint in checkpoint."""
    if isinstance(exc, (FileNotFoundError, PermissionError)):
        return False
    if isinstance(exc, OSError):
        errno = getattr(exc, "errno", None)
        if errno in (2,):  # ENOENT — missing artifact; retry without fixing inputs is pointless
            return False
    if isinstance(exc, ValueError):
        return False
    if isinstance(exc, RuntimeError):
        lowered = str(exc).lower()
        if "enabled=false" in lowered or "cannot resume" in lowered:
            return False
    return True


def _persist_resume_stage_failure(
    *,
    ckpt,
    stage: IngestStage,
    exc: BaseException,
    row: DocumentRecord,
    ingest_run: IngestionRunRecord,
    session: Session,
) -> None:
    retryable = _resume_failure_retryable(exc)
    mark_stage_failed(ckpt, stage, error=str(exc), retryable=retryable)
    row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
    ingest_run.status = "failed_retryable" if retryable else "failed_terminal"
    ingest_run.error_message = str(exc)[:8000]
    ingest_run.finished_at = datetime.now(UTC)
    session.commit()


def _retry_call(func, *args, **kwargs):
    runner = Retrying(
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    return runner(func, *args, **kwargs)


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


def _load_normalized_markdown_for_resume(*, document_id: str, settings: "Settings") -> str:
    """Return ``normalized.md`` text or raise ``FileNotFoundError`` if missing (local or S3)."""
    store = build_artifact_store(settings)
    norm_rel = canonical_normalized_md_rel(document_id)
    if not store.exists(norm_rel):
        raise FileNotFoundError(
            f"missing normalized artifact: {norm_rel.as_posix()} (under {store.root})"
        )
    return store.read_text(norm_rel, encoding="utf-8")


def parse_resume_stages_csv(stages_csv: str) -> list[IngestStage]:
    """Parse CLI `--stages` into an ordered canonical stage list."""

    raw = (stages_csv or "").strip().lower()
    if not raw:
        return [IngestStage.EMBED]
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        return [IngestStage.EMBED]

    mapping = {
        "embed": IngestStage.EMBED,
        "embeddings": IngestStage.EMBED,
        "claims": IngestStage.EXTRACT_CLAIMS,
        "extract_claims": IngestStage.EXTRACT_CLAIMS,
        "references": IngestStage.RESOLVE_REFERENCES,
        "resolve_references": IngestStage.RESOLVE_REFERENCES,
        "refs": IngestStage.RESOLVE_REFERENCES,
    }
    for tok in tokens:
        if mapping.get(tok) is None:
            raise ValueError(f"unsupported resume stage token: {tok!r}")

    desired = {mapping[tok] for tok in tokens}

    # Late-stage normalization: citations must be rebuilt before claims/embed if requested.
    ordered: list[IngestStage] = []
    for st in (
        IngestStage.RESOLVE_REFERENCES,
        IngestStage.EXTRACT_CLAIMS,
        IngestStage.EMBED,
    ):
        if st in desired:
            ordered.append(st)
    return ordered


def _run_resume_resolve_references(
    *,
    settings: "Settings",
    _session: Session,
    row: DocumentRecord,
    work_id: str,
    _ingest_workspace_ids: list[str] | None,
    ckpt: dict[str, Any],
    job_id: str | None,
    stage_session_factory: Any,
    stage_event_publisher: Any,
) -> None:
    if not settings.extraction_llm_enabled:
        raise RuntimeError(
            "Cannot resume references: extraction_llm_enabled=false "
            "(needs LLM refs extraction from normalized.md)."
        )

    normalized = _load_normalized_markdown_for_resume(document_id=row.id, settings=settings)
    source_path = Path(str(row.source_path or "unknown.pdf"))

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        _retry_call(neo.ensure_schema)

        # Prune prior outgoing cites to keep rebuild idempotent across fuzzy/unresolved refs.
        deleted = neo.detach_delete_outgoing_cites(work_id)
        if deleted:
            log.warning(
                "resume references: deleted outgoing CITES edges work_id=%s count=%s",
                work_id,
                deleted,
            )

        draft: WorkDraft | None = None
        authorships: list[Any] = []
        references: list[Any] = []
        oa_raw: dict[str, Any] | None = None

        norm_text = strip_repeated_boilerplate(
            normalize_text(strip_whole_document_markdown_fence(normalized)),
        )
        front = front_matter_slice(norm_text, max_chars=settings.front_matter_max_chars)
        ref_scope = build_references_scope_text(
            norm_text, max_chars=settings.references_scope_max_chars
        )

        progress_emit = None
        with stage(
            job_id,
            IngestStage.EXTRACT_META,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
            progress_emit=progress_emit,
            settings=settings,
        ) as st:
            draft, authorships, references, _ext_diag = extract_stages_llm_first(
                norm_text,
                settings,
                markdown_source="cached-normalized",
                document_id=row.id,
                source_name=source_path.name,
                front_matter_text=front.text,
                references_scope_text=ref_scope,
            )
            st.metric("references", len(references))
            st.metric("authorships", len(authorships))

            if draft and draft.doi:
                try:
                    oa = openalex_lookup_with_retry(draft.doi, settings.openalex_mailto)
                    if oa:
                        oa_raw = oa
                        draft = merge_draft_prefer_enriched(draft, draft_from_openalex(oa))
                except Exception as exc:  # noqa: BLE001
                    log.warning(
                        "resume references: OpenAlex enrichment failed doi=%s: %s", draft.doi, exc
                    )

        with stage(
            job_id,
            IngestStage.RESOLVE_REFERENCES,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
            progress_emit=None,
            settings=settings,
        ) as st:
            linked_refs = 0
            total_refs = len(references)
            seen = 0
            for ref in references:
                seen += 1
                if not (
                    normalize_doi(ref.doi)
                    or normalize_arxiv_id(ref.arxiv_id)
                    or (
                        normalized_title_for_fingerprint(ref.title) is not None
                        and ref.year is not None
                    )
                ):
                    continue
                _retry_call(persist_reference_citation, neo, work_id, ref, settings)
                linked_refs += 1
                if seen % 5 == 0 or seen == total_refs:
                    st.metric("subprogress_current", seen)
                    st.metric("subprogress_total", max(total_refs, 1))
                    st.flush_progress()
            st.metric("references_total", len(references))
            st.metric("references_linked", linked_refs)

        _retry_call(maybe_link_openalex_arxiv_version, neo, work_id, draft, oa_raw)
        del draft, authorships, references, oa_raw, norm_text
    finally:
        neo.close()

    mark_stage_completed(ckpt, IngestStage.RESOLVE_REFERENCES)


def _run_resume_extract_claims(
    *,
    settings: "Settings",
    document_id: str,
    work_id: str,
    ingest_workspace_ids: list[str] | None,
    ckpt: dict[str, Any],
    job_id: str | None,
    stage_session_factory: Any,
    stage_event_publisher: Any,
    refresh_claim_vectors: bool,
) -> None:
    if not settings.claims_extraction_enabled:
        raise RuntimeError(
            "Cannot resume claims: claims_extraction_enabled=false "
            "(enable claims extraction in Settings)."
        )

    normalized = _load_normalized_markdown_for_resume(document_id=document_id, settings=settings)
    doc_chunks = dedupe_chunks_for_embedding(
        chunk_document_for_retrieval_from_settings(normalized, settings),
    )

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        _retry_call(neo.ensure_schema)

        progress_emit = None
        claim_rows = run_extract_claims_stage(
            job_id=job_id,
            stage_session_factory=stage_session_factory,
            stage_event_publisher=stage_event_publisher,
            progress_emit=progress_emit,
            settings=settings,
            doc_chunks=doc_chunks,
            doc_id=document_id,
            work_id=work_id,
            retry_call=_retry_call,
            neo=neo,
        )

        if refresh_claim_vectors:
            try:
                embedder = resolve_embedder(settings)
                embedding_model = resolve_embedding_model_label(settings)
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
                    workspace_ids=ingest_workspace_ids,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning(
                    (
                        "resume claims: failed to refresh claim vectors in Qdrant "
                        "(continuing checkpoint): %s"
                    ),
                    exc,
                )

        del claim_rows
    finally:
        neo.close()

    mark_stage_completed(ckpt, IngestStage.EXTRACT_CLAIMS)


def resume_document_ingest_stages(
    *,
    document_id: str,
    stages_csv: str,
    settings: "Settings",
    session: Session,
    ingest_workspace_ids: list[str] | None = None,
    job_id: str | None = None,
    stage_session_factory: Any = None,
    stage_event_publisher: Any = None,
) -> str:
    """
    Resume selected late ingestion stages based on persisted ``normalized.md`` + SQL/N metadata.

    This is intentionally narrower than full `ingest_document` (does not rerun PDF extraction).
    """

    row = session.get(DocumentRecord, document_id)
    if row is None:
        raise ValueError(f"document_id not found: {document_id}")
    work_id = row.work_id
    if not work_id:
        raise ValueError(f"document {document_id} has no work_id; run full ingest first")

    stages = parse_resume_stages_csv(stages_csv)
    will_embed = IngestStage.EMBED in set(stages)

    ingest_run = IngestionRunRecord(
        document_id=document_id,
        status="running",
        finished_at=None,
    )
    session.add(ingest_run)
    session.flush()

    ckpt = parse_checkpoint(row.ingest_checkpoint_json)
    failure_persisted = False
    try:
        for st in stages:
            if st == IngestStage.RESOLVE_REFERENCES:
                try:
                    _run_resume_resolve_references(
                        settings=settings,
                        _session=session,
                        row=row,
                        work_id=work_id,
                        _ingest_workspace_ids=ingest_workspace_ids,
                        ckpt=ckpt,
                        job_id=job_id,
                        stage_session_factory=stage_session_factory,
                        stage_event_publisher=stage_event_publisher,
                    )
                except Exception as stage_exc:
                    _persist_resume_stage_failure(
                        ckpt=ckpt,
                        stage=IngestStage.RESOLVE_REFERENCES,
                        exc=stage_exc,
                        row=row,
                        ingest_run=ingest_run,
                        session=session,
                    )
                    failure_persisted = True
                    raise
            elif st == IngestStage.EXTRACT_CLAIMS:
                try:
                    _run_resume_extract_claims(
                        settings=settings,
                        document_id=document_id,
                        work_id=work_id,
                        ingest_workspace_ids=ingest_workspace_ids,
                        ckpt=ckpt,
                        job_id=job_id,
                        stage_session_factory=stage_session_factory,
                        stage_event_publisher=stage_event_publisher,
                        refresh_claim_vectors=not will_embed,
                    )
                except Exception as stage_exc:
                    _persist_resume_stage_failure(
                        ckpt=ckpt,
                        stage=IngestStage.EXTRACT_CLAIMS,
                        exc=stage_exc,
                        row=row,
                        ingest_run=ingest_run,
                        session=session,
                    )
                    failure_persisted = True
                    raise
            elif st == IngestStage.EMBED:
                reused_doc = True
                normalized = _load_normalized_markdown_for_resume(
                    document_id=document_id, settings=settings
                )
                doc_chunks = dedupe_chunks_for_embedding(
                    chunk_document_for_retrieval_from_settings(normalized, settings),
                )
                draft = minimal_work_draft_from_normalized_markdown(normalized)

                claim_rows: list[Any] = []
                try:
                    with stage(
                        job_id,
                        IngestStage.EMBED,
                        session_factory=stage_session_factory,
                        publisher=stage_event_publisher,
                        settings=settings,
                    ) as st:
                        run_ingest_embed_qdrant_phase(
                            settings=settings,
                            document_id=document_id,
                            work_id=work_id,
                            doc_chunks=doc_chunks,
                            claim_rows=claim_rows,
                            authorships=[],
                            draft=draft,
                            ingest_workspace_ids=ingest_workspace_ids,
                            st=st,
                            reused_doc=reused_doc,
                            retry_call=_retry_call,
                            logger=log,
                        )
                except Exception as embed_exc:
                    retryable = True
                    if isinstance(embed_exc, EmbeddingNonRetryableHttpError):
                        retryable = False
                    elif isinstance(embed_exc, EmbeddingCallError):
                        retryable = embed_exc.retryable
                    mark_stage_failed(
                        ckpt, IngestStage.EMBED, error=str(embed_exc), retryable=retryable
                    )
                    row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
                    ingest_run.status = "failed_retryable" if retryable else "failed_terminal"
                    ingest_run.error_message = str(embed_exc)[:8000]
                    ingest_run.finished_at = datetime.now(UTC)
                    session.commit()
                    failure_persisted = True
                    raise
                mark_stage_completed(ckpt, IngestStage.EMBED)

            else:  # pragma: no cover
                raise ValueError(f"unsupported resume stage: {st}")

        row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
        ingest_run.status = "completed"
        ingest_run.finished_at = datetime.now(UTC)
        session.commit()
        log.info(
            "resume stages completed document_id=%s work_id=%s stages=%s",
            document_id,
            work_id,
            stages,
        )
        return work_id

    except Exception as exc:
        if not failure_persisted:
            ingest_run.status = "failed_terminal"
            ingest_run.error_message = str(exc)[:8000]
            ingest_run.finished_at = datetime.now(UTC)
            row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
            session.commit()
        raise


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

    Expects ``normalized.md`` via the configured artifact store and ``DocumentRecord.work_id``.
    Updates ``ingest_checkpoint_json`` and appends an ``IngestionRunRecord`` on success/failure.

    Note: Implemented as a thin alias of :func:`resume_document_ingest_stages`
    with ``stages=embed``.
    """
    return resume_document_ingest_stages(
        document_id=document_id,
        stages_csv="embed",
        settings=settings,
        session=session,
        ingest_workspace_ids=ingest_workspace_ids,
        job_id=job_id,
        stage_session_factory=stage_session_factory,
        stage_event_publisher=stage_event_publisher,
    )
