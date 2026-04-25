"""In-process ingest worker internals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from opentelemetry import trace as trace_api
from sqlalchemy import select

from science_graphrag.api.ingest_event_bus import BUS
from science_graphrag.config import Settings
from science_graphrag.ingestion.pipeline import SkippedDuplicateIngestError, ingest_document
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobRecordOrm
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

from .dto import now_iso
from .registry import _registry

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


def _append_log(job_id: str, line: str) -> None:
    registry = _registry()
    chunk = f"[{now_iso()[11:19]}] {line}\n"
    with registry.lock:
        with registry._session_factory() as session:  # noqa: SLF001
            row = session.execute(
                select(IngestJobRecordOrm)
                .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                .limit(1)
            ).scalar_one_or_none()
            if not row:
                return
            row.logs = ((row.logs or "") + chunk)[-48_000:]
            session.commit()


def _ingest_workspace_tag(workspace_id: str) -> list[str]:
    workspace = workspace_id.strip()
    return [workspace] if workspace else []


def _publish_bus_event(
    *,
    job_id: str,
    parent_job_id: str | None,
    kind: str,
    payload: dict[str, Any],
) -> None:
    BUS.publish_threadsafe({"job_id": job_id, "kind": kind, "payload": payload})
    if parent_job_id:
        parent_payload = dict(payload)
        parent_payload["source_job_id"] = job_id
        BUS.publish_threadsafe({"job_id": parent_job_id, "kind": kind, "payload": parent_payload})


def _stage_event_publisher(job_id: str, parent_job_id: str | None = None):
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
            _publish_bus_event(
                job_id=job_id, parent_job_id=parent_job_id, kind="stage_started", payload=payload
            )
            return
        payload["finished_at"] = now
        if error:
            payload["error"] = error
            _publish_bus_event(
                job_id=job_id, parent_job_id=parent_job_id, kind="stage_failed", payload=payload
            )
            return
        _publish_bus_event(
            job_id=job_id, parent_job_id=parent_job_id, kind="stage_finished", payload=payload
        )

    return _publish


def _execute_single_ingest(job_id: str, temp_path: Path, settings: Settings) -> None:
    registry = _registry(settings)
    job = registry.get(job_id)
    if not job:
        return

    def upd(**kwargs: Any) -> None:
        registry._update(job_id, **kwargs)  # noqa: SLF001

    stage_publisher = _stage_event_publisher(job_id, job.parent_job_id)
    try:
        upd(status="running", message="Starting ingestion", progress_current=5)
        _append_log(job_id, f"Temp file {temp_path}")

        suffix = temp_path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            upd(
                status="failed",
                error="unsupported_file_type",
                message=f"Unsupported type {suffix!r}",
                finished_at=now_iso(),
            )
            _publish_bus_event(
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
            return

        upd(message="Running pipeline (Neo4j / vectors / SQL)…", progress_current=15)
        with chain_span(
            "api.ingest_job",
            {"job.id": job_id, "workspace.id": job.workspace_id, "input.file": temp_path.name},
        ):
            trace_ctx = trace_api.get_current_span().get_span_context()
            if trace_ctx.trace_id:
                registry._update(
                    job_id, phoenix_trace_id=format(trace_ctx.trace_id, "032x")
                )  # noqa: SLF001

            engine = get_engine(settings.database_url)
            init_db(engine)
            factory = session_factory(engine)
            work_id: str | None = None
            doc_id: str | None = None
            skipped = False
            ws_tag = _ingest_workspace_tag(job.workspace_id)
            try:
                with factory() as session:
                    with session.begin():
                        doc_id, work_id = ingest_document(
                            temp_path,
                            settings=settings,
                            session=session,
                            skip_existing_sha=False,
                            force_new_document=False,
                            ingest_workspace_ids=ws_tag,
                            job_id=job_id,
                            parent_job_id=job.parent_job_id,
                            stage_session_factory=registry._session_factory,  # noqa: SLF001
                            stage_event_publisher=stage_publisher,
                        )
            except SkippedDuplicateIngestError as dup:
                skipped = True
                doc_id = dup.document_id
                work_id = None
                _append_log(
                    job_id, f"Skipped duplicate sha256={dup.sha256} document_id={dup.document_id}"
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
                    _publish_bus_event(
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
                    return
                if work_id and not skipped:
                    with stage(
                        job_id,
                        IngestStage.ATTACH_WORKSPACE,
                        session_factory=registry._session_factory,  # noqa: SLF001
                        publisher=stage_publisher,
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
                            _publish_bus_event(
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
            _append_log(job_id, "Completed")
            _publish_bus_event(
                job_id=job_id,
                parent_job_id=job.parent_job_id,
                kind="terminal",
                payload={"job_id": job_id, "status": "completed", "finished_at": now_iso()},
            )
    except Exception as exc:  # noqa: BLE001
        _append_log(job_id, f"ERROR {exc!r}")
        upd(status="failed", error="ingest_failed", message=str(exc)[:500], finished_at=now_iso())
        _publish_bus_event(
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


def _run_ingest_thread(job_id: str, temp_path: Path, settings: Settings) -> None:
    try:
        _execute_single_ingest(job_id, temp_path, settings)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _refresh_parent_job(parent_id: str) -> None:
    registry = _registry()
    parent = registry.get(parent_id)
    if not parent or parent.kind != "batch_parent":
        return
    children = [cid for cid in parent.child_job_ids if cid]
    if not children:
        return
    statuses = []
    for child_id in children:
        child = registry.get(child_id)
        if child:
            statuses.append(child.status)
    failed = sum(1 for status in statuses if status == "failed")
    done = sum(1 for status in statuses if status in ("completed", "failed"))
    total = len(children)
    pct = int(100 * done / total) if total else 100
    if done < total:
        message = f"Batch running ({done}/{total})"
        status = "running"
    elif failed == total:
        message = f"Batch failed ({failed}/{total})"
        status = "failed"
    elif failed:
        ok = total - failed
        message = f"Batch finished: {ok} ok, {failed} failed (of {total})"
        status = "completed"
    else:
        message = f"Batch completed ({total} file(s))"
        status = "completed"
    registry._update(  # noqa: SLF001
        parent_id,
        status=status,
        message=message,
        progress_current=pct,
        progress_total=100,
        finished_at=now_iso() if done == total else parent.finished_at,
    )
    _publish_bus_event(
        job_id=parent_id,
        parent_job_id=None,
        kind="batch_progress",
        payload={
            "job_id": parent_id,
            "status": status,
            "message": message,
            "progress_current": pct,
            "progress_total": 100,
            "done_children": done,
            "total_children": total,
        },
    )
    if done == total:
        _publish_bus_event(
            job_id=parent_id,
            parent_job_id=None,
            kind="terminal",
            payload={"job_id": parent_id, "status": status, "finished_at": now_iso()},
        )


def _run_batch_thread(
    parent_id: str, child_paths: list[tuple[str, Path]], settings: Settings
) -> None:
    registry = _registry(settings)
    parent = registry.get(parent_id)
    if not parent:
        for _, path in child_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return
    registry._update(  # noqa: SLF001
        parent_id,
        status="running",
        message=f"Processing {len(child_paths)} file(s)…",
        progress_current=0,
        progress_total=100,
    )
    try:
        for child_id, path in child_paths:
            _execute_single_ingest(child_id, path, settings)
            _refresh_parent_job(parent_id)
    finally:
        for _, path in child_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        _refresh_parent_job(parent_id)
