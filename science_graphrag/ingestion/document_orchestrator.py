"""Application-level orchestration for one ingest document run."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Callable

import httpx
from opentelemetry import trace as trace_api
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from science_graphrag.dedup.entity_ingest_conflict_check import (
    enqueue_entity_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.dedup.ingest_conflict_check import (
    enqueue_author_near_duplicate_conflicts_on_ingest,
    enqueue_work_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.domain.models import ReferenceDraft
from science_graphrag.embeddings import resolve_embedding_model_label
from science_graphrag.embeddings.errors import EmbeddingCallError, EmbeddingNonRetryableHttpError
from science_graphrag.ingestion.artifact_layout import canonical_normalized_md_rel
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
from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.ingestion.document_slices import (
    build_references_scope_text,
    front_matter_slice,
    strip_repeated_boilerplate,
)
from science_graphrag.ingestion.institution_nodes import institution_nodes_from_authorships
from science_graphrag.ingestion.markdown_fence import strip_whole_document_markdown_fence
from science_graphrag.ingestion.normalize import normalize_text
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.ingestion.stage_graph import build_runtime_state, load_checkpoint_from_session
from science_graphrag.ingestion.stages.claims import run_claims_phase
from science_graphrag.ingestion.stages.embeddings import run_embeddings_phase
from science_graphrag.ingestion.stages.metadata import merge_draft_prefer_enriched
from science_graphrag.observability.phoenix_tracer import (
    OpenInferenceAttributes,
    SpanAttributes,
    chain_span,
    set_span_attributes,
)
from science_graphrag.storage.models_orm import (
    DocumentRecord,
    IngestionRunRecord,
    IngestJobRecordOrm,
)
from science_graphrag.utils.ingest_pipeline_log_heartbeat import pipeline_log_heartbeat_run
from science_graphrag.utils.ingest_vl_log_heartbeat import (
    VlLogHeartbeatState,
    maybe_log_vl_page_heartbeat,
    maybe_log_vl_parse_started,
)


@dataclass(slots=True)
class DocumentOrchestrationDeps:
    """Injectable dependencies used by document ingestion orchestration."""

    markdown_from_path: Callable[..., tuple[str, str, dict[str, Any] | None]]
    write_markdown_artifact: Callable[..., Path]
    write_extraction_diagnostics_json: Callable[..., Path]
    openalex_lookup_with_retry: Callable[[str, str], dict[str, Any] | None]
    resolve_work_id: Callable[..., str]
    venue_id: Callable[[str | None], str]
    persist_reference_citation: Callable[..., None]
    maybe_link_openalex_arxiv_version: Callable[..., None]
    normalize_arxiv_id: Callable[[str | None], str | None]
    normalized_title_for_fingerprint: Callable[[str | None], str | None]
    retry_call: Callable[..., Any]
    sql_commit_if_session: Callable[[Session | None], None]
    build_artifact_store: Callable[[Any], Any]
    neo4j_store_class: Any
    logger: Any


def run_document_orchestration(
    *,
    path: Path,
    settings: Any,
    session: Session | None,
    doc_id: str,
    sha: str,
    reused_doc: bool,
    ingest_workspace_ids: list[str] | None,
    job_id: str | None,
    parent_job_id: str | None,
    stage_session_factory: Any | None,
    stage_event_publisher: Any | None,
    stage_progress_publisher: Any | None,
    bypass_markdown_cache: bool,
    deps: DocumentOrchestrationDeps,
) -> tuple[str, str]:
    """Execute document-level ingest stage graph and persistence."""
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
    pipeline_hb_ctx = (
        pipeline_log_heartbeat_run() if (job_id and stage_session_factory) else nullcontext()
    )

    with chain_span("ingest_document", root_attrs), pipeline_hb_ctx:
        progress_emit = stage_progress_publisher
        runtime_state = build_runtime_state(
            settings=settings,
            document_id=doc_id,
            sha256=sha,
            reused_document=reused_doc,
            workspace_id=workspace_id,
            progress_emit=progress_emit,
            ingest_workspace_ids=ingest_workspace_ids,
        )
        load_checkpoint_from_session(
            runtime_state,
            session=session,
            parse_checkpoint=parse_checkpoint,
            default_checkpoint=default_checkpoint,
        )
        ckpt: dict[str, Any] = runtime_state.checkpoint

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
            progress_emit=progress_emit,
            settings=settings,
        ) as st:
            vl_log_hb = VlLogHeartbeatState()

            def _on_vl_pages(done: int, tot: int) -> None:
                st.metric("vl_pages_total", tot)
                st.metric("vl_pages_processed", done)
                st.metric("detail_message", f"PDF pages {done}/{tot}")
                st.metric("subprogress_current", done)
                st.metric("subprogress_total", tot)
                st.flush_progress()
                maybe_log_vl_page_heartbeat(
                    deps.logger, vl_log_hb, pages_done=done, pages_total=tot
                )

            def _on_vl_batches_ready(batch_count: int, page_count: int, batch_sz: int) -> None:
                st.metric("vl_batch_total", int(batch_count))
                st.metric("vl_batch_size", int(batch_sz))
                if int(batch_count) == 1:
                    st.metric("detail_message", "Waiting for vision model response")
                st.flush_progress()
                maybe_log_vl_parse_started(
                    deps.logger,
                    vl_log_hb,
                    batch_count=int(batch_count),
                    page_total=int(page_count),
                    batch_size=int(batch_sz),
                )

            markdown_text, extraction_mode, vl_stats = deps.markdown_from_path(
                path,
                settings,
                document_id=doc_id,
                on_vl_page_progress=_on_vl_pages if job_id and stage_session_factory else None,
                on_vl_batches_ready=(
                    _on_vl_batches_ready if job_id and stage_session_factory else None
                ),
                bypass_markdown_cache=bypass_markdown_cache,
            )
            set_span_attributes({"metadata.extraction_mode": extraction_mode})
            st.metric("source_suffix", path.suffix.lower())
            st.metric("extraction_mode", extraction_mode)

        ingest_artifact_store = deps.build_artifact_store(settings)
        deps.write_markdown_artifact(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            markdown=markdown_text,
            extraction_mode=extraction_mode,
            artifact_store=ingest_artifact_store,
        )
        normalized = strip_repeated_boilerplate(
            normalize_text(strip_whole_document_markdown_fence(markdown_text))
        )
        ingest_artifact_store.write_text(canonical_normalized_md_rel(doc_id), normalized)
        front = front_matter_slice(normalized, max_chars=settings.front_matter_max_chars)
        ref_scope = build_references_scope_text(
            normalized, max_chars=settings.references_scope_max_chars
        )

        with stage(
            job_id,
            IngestStage.EXTRACT_META,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
            progress_emit=progress_emit,
            settings=settings,
        ) as st:
            from science_graphrag.ingestion.llm.stage_extraction import extract_stages_llm_first

            with chain_span(
                "ingest.extract_meta.metadata_and_refs",
                {"document.id": doc_id, "document.source_name": path.name},
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
            fb_reason = vl_stats.get("markdown_fallback_error_type")
            fb_msg = vl_stats.get("markdown_fallback_error_message")
            if fb_reason or fb_msg:
                ext_diag.fallback_reasons.append(
                    {
                        "stage": "parse_pdf",
                        "kind": "vl_markdown_fallback",
                        "from": vl_stats.get("markdown_fallback_from"),
                        "to": vl_stats.get("markdown_fallback_to"),
                        "transport": vl_stats.get("ingest_transport"),
                        "error_type": fb_reason,
                        "error_message": fb_msg,
                    },
                )
        deps.write_extraction_diagnostics_json(
            settings=settings,
            document_id=doc_id,
            source_path=path,
            diagnostics_json=ext_diag.to_json(),
            artifact_store=ingest_artifact_store,
        )

        oa_raw: dict[str, Any] | None = None
        with stage(
            job_id,
            IngestStage.ENRICH_OPENALEX,
            session_factory=stage_session_factory,
            publisher=stage_event_publisher,
            progress_emit=progress_emit,
            settings=settings,
        ) as st:
            with chain_span("ingest.enrich_openalex.lookup"):
                SpanAttributes.set_input({"doi": draft.doi})
                if draft.doi:
                    try:
                        oa = deps.openalex_lookup_with_retry(draft.doi, settings.openalex_mailto)
                        if oa:
                            from science_graphrag.ingestion.enrichment.openalex import (
                                draft_from_openalex,
                            )

                            oa_raw = oa
                            draft = merge_draft_prefer_enriched(draft, draft_from_openalex(oa))
                            set_span_attributes({"openalex.found": True})
                        else:
                            set_span_attributes({"openalex.found": False})
                    except (
                        httpx.HTTPError,
                        json.JSONDecodeError,
                        ValueError,
                        TypeError,
                        KeyError,
                        AttributeError,
                        RuntimeError,
                        TimeoutError,
                        OSError,
                    ) as exc:
                        set_span_attributes({"openalex.found": False})
                        deps.logger.warning(
                            "OpenAlex enrichment failed for doi=%s: %s", draft.doi, exc
                        )
            st.metric("has_doi", int(bool(draft.doi)))
            st.metric("enriched", int(bool(oa_raw)))

        neo = deps.neo4j_store_class(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        try:
            deps.retry_call(neo.ensure_schema)
            work_id = deps.resolve_work_id(neo, draft)
            vid = deps.venue_id(draft.venue_name)

            with stage(
                job_id,
                IngestStage.ENRICH_ROR,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
            ) as st:
                inst_nodes = institution_nodes_from_authorships(authorships, settings)
                st.metric("institutions", len(inst_nodes))

            with stage(
                job_id,
                IngestStage.WRITE_GRAPH,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
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
                    except (
                        SQLAlchemyError,
                        httpx.HTTPError,
                        OSError,
                        RuntimeError,
                        ValueError,
                        TypeError,
                        KeyError,
                        AttributeError,
                    ) as exc:
                        deps.logger.warning("ingest_dedup_conflict_check_failed: %s", exc)
                deps.retry_call(
                    neo.upsert_work_layer1,
                    work_id,
                    draft,
                    authorships,
                    venue_id=vid,
                    institution_nodes=inst_nodes,
                )
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
                    except (
                        SQLAlchemyError,
                        httpx.HTTPError,
                        OSError,
                        RuntimeError,
                        ValueError,
                        TypeError,
                        KeyError,
                        AttributeError,
                    ) as exc:
                        deps.logger.warning("ingest_author_dedup_conflict_check_failed: %s", exc)
                    try:
                        enqueue_entity_near_duplicate_conflicts_on_ingest(
                            session=session,
                            neo=neo,
                            workspace_id=workspace_id,
                            new_work_id=work_id,
                            settings=settings,
                        )
                    except (
                        SQLAlchemyError,
                        httpx.HTTPError,
                        OSError,
                        RuntimeError,
                        ValueError,
                        TypeError,
                        KeyError,
                        AttributeError,
                    ) as exc:
                        deps.logger.warning("ingest_entity_dedup_conflict_check_failed: %s", exc)

            with stage(
                job_id,
                IngestStage.RESOLVE_REFERENCES,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
            ) as st:
                linked_refs = 0
                total_refs = len(references)
                seen = 0
                for ref in references:
                    ref = ref if isinstance(ref, ReferenceDraft) else ref
                    seen += 1
                    if not (
                        normalize_doi(ref.doi)
                        or deps.normalize_arxiv_id(ref.arxiv_id)
                        or (
                            deps.normalized_title_for_fingerprint(ref.title) is not None
                            and ref.year is not None
                        )
                    ):
                        continue
                    deps.retry_call(deps.persist_reference_citation, neo, work_id, ref, settings)
                    linked_refs += 1
                    if seen % 5 == 0 or seen == total_refs:
                        st.metric("subprogress_current", seen)
                        st.metric("subprogress_total", max(total_refs, 1))
                        st.flush_progress()
                st.metric("references_total", len(references))
                st.metric("references_linked", linked_refs)

            deps.retry_call(deps.maybe_link_openalex_arxiv_version, neo, work_id, draft, oa_raw)

            with stage(
                job_id,
                IngestStage.CHUNK,
                session_factory=stage_session_factory,
                publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
            ) as st:
                doc_chunks = dedupe_chunks_for_embedding(
                    chunk_document_for_retrieval_from_settings(normalized, settings),
                )
                st.metric("chunks", len(doc_chunks))

            claim_rows = run_claims_phase(
                job_id=job_id,
                stage_session_factory=stage_session_factory,
                stage_event_publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
                doc_chunks=doc_chunks,
                doc_id=doc_id,
                work_id=work_id,
                retry_call=deps.retry_call,
                neo=neo,
            )
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
            deps.sql_commit_if_session(session)

        try:
            run_embeddings_phase(
                job_id=job_id,
                stage_session_factory=stage_session_factory,
                stage_event_publisher=stage_event_publisher,
                progress_emit=progress_emit,
                settings=settings,
                document_id=doc_id,
                work_id=work_id,
                doc_chunks=doc_chunks,
                claim_rows=claim_rows,
                authorships=authorships,
                draft=draft,
                ingest_workspace_ids=ingest_workspace_ids,
                reused_doc=reused_doc,
                retry_call=deps.retry_call,
                logger=deps.logger,
            )
        except Exception as embed_exc:
            if session is not None:
                retryable = True
                if isinstance(embed_exc, EmbeddingNonRetryableHttpError):
                    retryable = False
                elif isinstance(embed_exc, EmbeddingCallError):
                    retryable = embed_exc.retryable
                mark_stage_failed(
                    ckpt, IngestStage.EMBED, error=str(embed_exc), retryable=retryable
                )
                row = session.get(DocumentRecord, doc_id)
                if row is not None:
                    row.ingest_checkpoint_json = serialize_checkpoint(ckpt)
                if ingest_run is not None:
                    ingest_run.status = "failed_retryable" if retryable else "failed_terminal"
                    ingest_run.error_message = str(embed_exc)[:8000]
                    ingest_run.finished_at = datetime.now(UTC)
                deps.sql_commit_if_session(session)
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
            deps.sql_commit_if_session(session)

        return doc_id, work_id
