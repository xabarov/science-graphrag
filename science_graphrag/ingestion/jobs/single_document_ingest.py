"""Single-document and batch-parent ingest execution (no FastAPI)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from opentelemetry import trace as trace_api

from science_graphrag.api.ingest.dto import job_record_to_view, now_iso
from science_graphrag.config import Settings
from science_graphrag.ingestion.jobs.ingest_job_bus import publish_ingest_job_event
from science_graphrag.ingestion.jobs.registry import get_ingest_job_registry
from science_graphrag.ingestion.pipeline import SkippedDuplicateIngestError, ingest_document
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.ingest_queue_store import build_ingest_queue_store
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.utils.log_context import ingest_log_context

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


def append_ingest_job_log(job_id: str, line: str, *, settings: Settings | None = None) -> None:
    """Append a line to the durable ingest job log (uses registry for ``settings`` DSN)."""
    get_ingest_job_registry(settings).append_job_log_line(job_id, line)


def _ingest_workspace_tag(workspace_id: str) -> list[str]:
    workspace = workspace_id.strip()
    return [workspace] if workspace else []


def sse_progress_canonical_fields(job_id: str, settings: Settings) -> dict[str, Any]:
    """Re-read job from DB and attach canonical progress fields for ``stage_progress`` SSE."""
    rec = get_ingest_job_registry(settings).get_job(job_id)
    if rec is None:
        return {}
    try:
        view = job_record_to_view(rec)
    except Exception:  # noqa: BLE001
        logger.debug("sse snapshot: job_record_to_view failed", exc_info=True)
        return {}
    out: dict[str, Any] = {
        "ingest_phase": view.ingest_phase,
        "active_stage": view.active_stage,
    }
    if view.progress_pct is not None:
        out["progress_pct"] = float(view.progress_pct)
    if view.detail_message is not None:
        out["detail_message"] = view.detail_message
    if view.subprogress_current is not None:
        out["subprogress_current"] = view.subprogress_current
    if view.subprogress_total is not None:
        out["subprogress_total"] = view.subprogress_total
    out["progress_indeterminate"] = bool(view.progress_indeterminate)
    return out


def _stage_event_publisher(
    job_id: str,
    parent_job_id: str | None,
    settings: Settings,
) -> tuple[Any, Any]:
    def _publish(
        stage_name: IngestStage, status: str, metrics: dict[str, Any], error: str | None
    ) -> None:
        now = now_iso()
        payload: dict[str, Any] = {
            "job_id": job_id,
            "stage": stage_name.value,
            "status": status,
            "metrics": dict(metrics or {}),
        }
        if status == "running":
            payload["started_at"] = now
            publish_ingest_job_event(
                job_id=job_id, parent_job_id=parent_job_id, kind="stage_started", payload=payload
            )
            return
        payload["finished_at"] = now
        if error:
            payload["error"] = error
            publish_ingest_job_event(
                job_id=job_id, parent_job_id=parent_job_id, kind="stage_failed", payload=payload
            )
            return
        publish_ingest_job_event(
            job_id=job_id, parent_job_id=parent_job_id, kind="stage_finished", payload=payload
        )

    def _progress(stage_name: IngestStage, metrics: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "job_id": job_id,
            "stage": stage_name.value,
            "status": "running",
            "metrics": dict(metrics or {}),
        }
        try:
            extras = sse_progress_canonical_fields(job_id, settings)
            if extras:
                payload.update(extras)
        except Exception:  # noqa: BLE001
            logger.debug("sse snapshot: merge failed", exc_info=True)
        publish_ingest_job_event(
            job_id=job_id, parent_job_id=parent_job_id, kind="stage_progress", payload=payload
        )

    return _publish, _progress


def execute_single_ingest(job_id: str, temp_path: Path, settings: Settings) -> None:
    registry = get_ingest_job_registry(settings)
    job = registry.get(job_id)
    if not job:
        return
    ws_id = (job.workspace_id or "").strip() or None
    with ingest_log_context(job_id=job_id, workspace_id=ws_id):
        _execute_single_ingest_body(job_id, temp_path, settings, registry, job)


def _execute_single_ingest_body(  # pylint: disable=too-many-locals,too-many-statements
    job_id: str,
    temp_path: Path,
    settings: Settings,
    registry: Any,
    job: Any,
) -> None:
    t0 = time.perf_counter()
    terminal_state: dict[str, Any] = {"emitted": False}

    def _emit_worker_terminal(
        outcome: str,
        *,
        error_code: str | None = None,
        skipped_duplicate: bool | None = None,
    ) -> None:
        if terminal_state["emitted"]:
            return
        terminal_state["emitted"] = True
        duration_ms = int((time.perf_counter() - t0) * 1000)
        kind = str(getattr(job, "kind", "") or "")
        skip_part = (
            "" if skipped_duplicate is None else f" skipped_duplicate={bool(skipped_duplicate)}"
        )
        logger.info(
            "ingest worker: terminal outcome=%s kind=%s duration_ms=%s error_code=%s%s",
            outcome,
            kind,
            duration_ms,
            error_code or "-",
            skip_part,
            extra={"stage": "worker_terminal"},
        )

    def upd(**kwargs: Any) -> None:
        registry.update_job(job_id, **kwargs)

    stage_publisher, stage_progress_publisher = _stage_event_publisher(
        job_id, job.parent_job_id, settings
    )
    try:
        upd(status="running", message="Starting ingestion", progress_current=5)
        logger.info(
            "ingest worker: execution started",
            extra={"stage": "worker_start"},
        )
        append_ingest_job_log(job_id, f"Temp file {temp_path}", settings=settings)

        suffix = temp_path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            upd(
                status="failed",
                error="unsupported_file_type",
                message=f"Unsupported type {suffix!r}",
                finished_at=now_iso(),
            )
            publish_ingest_job_event(
                job_id=job_id,
                parent_job_id=job.parent_job_id,
                kind="terminal",
                payload={
                    "job_id": job_id,
                    "status": "failed",
                    "error": "unsupported_file_type",
                    "finished_at": now_iso(),
                },
            )
            _emit_worker_terminal("failed", error_code="unsupported_file_type")
            return

        upd(message="Running pipeline (Neo4j / vectors / SQL)…", progress_current=15)
        with chain_span(
            "api.ingest_job",
            {"job.id": job_id, "workspace.id": job.workspace_id, "input.file": temp_path.name},
        ):
            trace_ctx = trace_api.get_current_span().get_span_context()
            if trace_ctx.trace_id:
                registry.update_job(job_id, phoenix_trace_id=format(trace_ctx.trace_id, "032x"))

            engine = get_engine(settings.database_url)
            init_db(engine)
            factory = session_factory(engine)
            work_id: str | None = None
            doc_id: str | None = None
            skipped = False
            ws_tag = _ingest_workspace_tag(job.workspace_id)
            try:
                with factory() as session:
                    doc_id, work_id = ingest_document(
                        temp_path,
                        settings=settings,
                        session=session,
                        skip_existing_sha=False,
                        force_new_document=False,
                        ingest_workspace_ids=ws_tag,
                        job_id=job_id,
                        parent_job_id=job.parent_job_id,
                        stage_session_factory=registry.job_session_factory,
                        stage_event_publisher=stage_publisher,
                        stage_progress_publisher=stage_progress_publisher,
                    )
            except SkippedDuplicateIngestError as dup:
                skipped = True
                doc_id = dup.document_id
                work_id = None
                append_ingest_job_log(
                    job_id,
                    f"Skipped duplicate sha256={dup.sha256} document_id={dup.document_id}",
                    settings=settings,
                )

            upd(progress_current=85, message="Attaching to workspace…")
            store = Neo4jGraphStore(
                settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
            )
            try:
                workspace = store.workspace_get(job.workspace_id)
                if not workspace:
                    upd(
                        status="failed",
                        error="workspace_not_found",
                        message="Workspace not found",
                        finished_at=now_iso(),
                    )
                    publish_ingest_job_event(
                        job_id=job_id,
                        parent_job_id=job.parent_job_id,
                        kind="terminal",
                        payload={
                            "job_id": job_id,
                            "status": "failed",
                            "error": "workspace_not_found",
                            "finished_at": now_iso(),
                        },
                    )
                    _emit_worker_terminal("failed", error_code="workspace_not_found")
                    return
                if work_id and not skipped:
                    with stage(
                        job_id,
                        IngestStage.ATTACH_WORKSPACE,
                        session_factory=registry.job_session_factory,
                        publisher=stage_publisher,
                        progress_emit=stage_progress_publisher,
                        settings=settings,
                    ) as st:
                        st.metric("workspace_id", job.workspace_id)
                        if not store.workspace_add_work(job.workspace_id, str(work_id)):
                            upd(
                                status="failed",
                                error="work_attach_failed",
                                message=(
                                    "Ingest OK but could not attach work to workspace "
                                    "(invalid work_id?)"
                                ),
                                document_id=doc_id,
                                work_id=work_id,
                                finished_at=now_iso(),
                            )
                            publish_ingest_job_event(
                                job_id=job_id,
                                parent_job_id=job.parent_job_id,
                                kind="terminal",
                                payload={
                                    "job_id": job_id,
                                    "status": "failed",
                                    "error": "work_attach_failed",
                                    "finished_at": now_iso(),
                                },
                            )
                            _emit_worker_terminal("failed", error_code="work_attach_failed")
                            return
            finally:
                store.close()

            upd(
                status="completed",
                message="Done" if not skipped else "Duplicate bytes skipped (existing document)",
                progress_current=100,
                document_id=doc_id,
                work_id=work_id,
                skipped_duplicate=skipped,
                finished_at=now_iso(),
            )
            append_ingest_job_log(job_id, "Completed", settings=settings)
            publish_ingest_job_event(
                job_id=job_id,
                parent_job_id=job.parent_job_id,
                kind="terminal",
                payload={"job_id": job_id, "status": "completed", "finished_at": now_iso()},
            )
            _emit_worker_terminal(
                "completed",
                error_code=None,
                skipped_duplicate=skipped,
            )
            qkey = job.queued_source_object_key
            if qkey:
                try:
                    build_ingest_queue_store(settings).delete(qkey)
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        append_ingest_job_log(job_id, f"ERROR {exc!r}", settings=settings)
        upd(status="failed", error="ingest_failed", message=str(exc)[:500], finished_at=now_iso())
        publish_ingest_job_event(
            job_id=job_id,
            parent_job_id=job.parent_job_id,
            kind="terminal",
            payload={
                "job_id": job_id,
                "status": "failed",
                "error": str(exc)[:500],
                "finished_at": now_iso(),
            },
        )
        _emit_worker_terminal("failed", error_code="ingest_failed")
