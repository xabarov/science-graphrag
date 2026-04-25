"""Background ingest jobs for workspace uploads (PDF / MD / TXT) with polling."""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from opentelemetry import trace as trace_api
from pydantic import BaseModel, Field
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from science_graphrag.api.ingest_event_bus import BUS
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.pipeline import SkippedDuplicateIngestError, ingest_document
from science_graphrag.ingestion.stage_context import IngestStage, stage
from science_graphrag.observability.phoenix_tracer import chain_span
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobRecordOrm, IngestJobStageOrm
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})
BATCH_MAX_FILES = 200
_REGISTRY_LOCK = threading.Lock()
_REGISTRY_BOX: dict[str, IngestJobRegistry | None] = {"value": None}


def _registry(settings: Settings | None = None):
    registry = _REGISTRY_BOX["value"]
    if registry is not None:
        return registry
    with _REGISTRY_LOCK:
        registry = _REGISTRY_BOX["value"]
        if registry is None:
            registry = IngestJobRegistry(settings or get_settings())
            _REGISTRY_BOX["value"] = registry
    return registry


def _append_log(job_id: str, line: str) -> None:
    registry = _registry()
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    chunk = f"[{ts}] {line}\n"
    with registry.lock:
        with registry._session_factory() as session:
            row = session.execute(
                select(IngestJobRecordOrm)
                .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                .limit(1)
            ).scalar_one_or_none()
            if not row:
                return
            row.logs = ((row.logs or "") + chunk)[-48_000:]
            session.commit()


@dataclass
class IngestJobRecord:
    job_id: str
    workspace_id: str
    filename: str
    status: str  # queued | running | completed | failed
    message: str = ""
    progress_current: int = 0
    progress_total: int = 100
    logs: str = ""
    work_id: str | None = None
    document_id: str | None = None
    skipped_duplicate: bool = False
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    finished_at: str | None = None
    kind: str = "single"  # single | batch_parent | batch_child
    parent_job_id: str | None = None
    child_job_ids: list[str] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    phoenix_trace_id: str | None = None


class IngestJobRegistry:
    """Durable ingest job store backed by Postgres."""

    def __init__(self, settings: Settings) -> None:
        self.lock = threading.Lock()
        self._settings = settings
        self._engine = get_engine(settings.database_url)
        init_db(self._engine)
        self._session_factory = session_factory(self._engine)
        self.mark_stale_running_jobs_failed()

    @staticmethod
    def _to_dataclass(
        row: IngestJobRecordOrm, stages: list[dict[str, Any]] | None = None
    ) -> IngestJobRecord:
        stage_rows = list(stages or [])
        progress_current = int(row.progress_current or 0)
        progress_total = int(row.progress_total or 100)
        if row.kind == "single" and stage_rows:
            completed = sum(1 for item in stage_rows if item.get("status") == "completed")
            progress_total = max(progress_total, 100)
            progress_current = int((completed / max(len(IngestStage), 1)) * 100)
        return IngestJobRecord(
            job_id=row.job_id,
            workspace_id=row.workspace_id,
            filename=row.filename,
            status=row.status,
            message=row.message or "",
            progress_current=progress_current,
            progress_total=progress_total,
            logs=row.logs or "",
            work_id=row.work_id,
            document_id=row.document_id,
            skipped_duplicate=bool(row.skipped_duplicate),
            error=row.error,
            created_at=row.created_at.isoformat() if row.created_at else _now_iso(),
            finished_at=row.finished_at.isoformat() if row.finished_at else None,
            kind=row.kind or "single",
            parent_job_id=row.parent_job_id,
            child_job_ids=row.child_job_ids,
            stages=stage_rows,
            phoenix_trace_id=row.phoenix_trace_id,
        )

    @staticmethod
    def _stage_to_dict(row: IngestJobStageOrm) -> dict[str, Any]:
        started_iso = row.started_at.isoformat() if row.started_at else None
        finished_iso = row.finished_at.isoformat() if row.finished_at else None
        duration_ms = None
        if row.started_at and row.finished_at:
            duration_ms = max(0, int((row.finished_at - row.started_at).total_seconds() * 1000))
        metrics: dict[str, Any] = {}
        raw_metrics = (row.metrics_json or "").strip()
        if raw_metrics:
            try:
                parsed = json.loads(raw_metrics)
                if isinstance(parsed, dict):
                    metrics = parsed
            except Exception:
                metrics = {}
        return {
            "name": row.stage,
            "status": row.status,
            "started_at": started_iso,
            "finished_at": finished_iso,
            "duration_ms": duration_ms,
            "metrics": metrics,
            "error": row.error,
        }

    def _load_job_stages(self, session: Any, job_id: str) -> list[dict[str, Any]]:
        stage_rows = (
            session.execute(
                select(IngestJobStageOrm)
                .where(IngestJobStageOrm.job_id == str(job_id).strip())
                .order_by(IngestJobStageOrm.started_at.asc(), IngestJobStageOrm.stage.asc())
            )
            .scalars()
            .all()
        )
        return [self._stage_to_dict(row) for row in stage_rows]

    def mark_stale_running_jobs_failed(self) -> None:
        with self.lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(IngestJobRecordOrm).where(
                        IngestJobRecordOrm.status.in_(("queued", "running"))
                    )
                ).scalars()
                changed = False
                for row in rows:
                    row.status = "failed"
                    row.error = row.error or "server_restarted"
                    row.message = "Job interrupted by API restart"
                    row.finished_at = datetime.now(UTC)
                    changed = True
                if changed:
                    session.commit()

    def create_job(
        self,
        workspace_id: str,
        filename: str,
        *,
        kind: str = "single",
        parent_job_id: str | None = None,
    ) -> IngestJobRecord:
        job_id = str(uuid.uuid4())
        BUS.cleanup_old_events(ttl_hours=24)
        with self.lock:
            with self._session_factory() as session:
                row = IngestJobRecordOrm(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    filename=filename,
                    status="queued",
                    message="Queued",
                    kind=kind,
                    parent_job_id=parent_job_id,
                )
                session.add(row)
                session.commit()
                session.refresh(row)
                return self._to_dataclass(row)

    def get(self, job_id: str) -> IngestJobRecord | None:
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return None
                stages = self._load_job_stages(session, job_id)
                return self._to_dataclass(row, stages=stages)

    def _update(self, job_id: str, **kwargs: Any) -> None:
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return
                for k, v in kwargs.items():
                    if k == "created_at":
                        continue
                    if k == "finished_at":
                        row.finished_at = (
                            datetime.fromisoformat(v) if isinstance(v, str) and v else v
                        )
                        continue
                    if k == "child_job_ids":
                        row.child_job_ids = [str(x) for x in (v or []) if x]
                        continue
                    setattr(row, k, v)
                session.commit()


def _ingest_workspace_tag(workspace_id: str) -> list[str]:
    w = workspace_id.strip()
    return [w] if w else []


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
        now_iso = _now_iso()
        payload: dict[str, Any] = {
            "job_id": job_id,
            "stage": stage_name.value,
            "status": status,
            "metrics": dict(metrics or {}),
        }
        if status == "running":
            payload["started_at"] = now_iso
            _publish_bus_event(
                job_id=job_id, parent_job_id=parent_job_id, kind="stage_started", payload=payload
            )
            return
        payload["finished_at"] = now_iso
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
        registry._update(job_id, **kwargs)

    stage_publisher = _stage_event_publisher(job_id, job.parent_job_id)
    try:
        upd(status="running", message="Starting ingestion", progress_current=5)
        _append_log(job_id, f"Temp file {temp_path}")

        suf = temp_path.suffix.lower()
        if suf not in SUPPORTED_SUFFIXES:
            upd(
                status="failed",
                error="unsupported_file_type",
                message=f"Unsupported type {suf!r}",
                finished_at=_now_iso(),
            )
            _publish_bus_event(
                job_id=job_id,
                parent_job_id=job.parent_job_id,
                kind="terminal",
                payload={
                    "job_id": job_id,
                    "status": "failed",
                    "error": "unsupported_file_type",
                    "finished_at": _now_iso(),
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
                registry._update(job_id, phoenix_trace_id=format(trace_ctx.trace_id, "032x"))

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
                            stage_session_factory=registry._session_factory,
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
                ws = store.workspace_get(job.workspace_id)
                if not ws:
                    upd(
                        status="failed",
                        error="workspace_not_found",
                        message="Workspace not found",
                        finished_at=_now_iso(),
                    )
                    _publish_bus_event(
                        job_id=job_id,
                        parent_job_id=job.parent_job_id,
                        kind="terminal",
                        payload={
                            "job_id": job_id,
                            "status": "failed",
                            "error": "workspace_not_found",
                            "finished_at": _now_iso(),
                        },
                    )
                    return
                if work_id and not skipped:
                    with stage(
                        job_id,
                        IngestStage.ATTACH_WORKSPACE,
                        session_factory=registry._session_factory,
                        publisher=stage_publisher,
                    ) as st:
                        st.metric("workspace_id", job.workspace_id)
                        if not store.workspace_add_work(job.workspace_id, str(work_id)):
                            upd(
                                status="failed",
                                error="work_attach_failed",
                                message="Ingest OK but could not attach work to workspace (invalid work_id?)",
                                document_id=doc_id,
                                work_id=work_id,
                                finished_at=_now_iso(),
                            )
                            _publish_bus_event(
                                job_id=job_id,
                                parent_job_id=job.parent_job_id,
                                kind="terminal",
                                payload={
                                    "job_id": job_id,
                                    "status": "failed",
                                    "error": "work_attach_failed",
                                    "finished_at": _now_iso(),
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
                finished_at=_now_iso(),
            )
            _append_log(job_id, "Completed")
            _publish_bus_event(
                job_id=job_id,
                parent_job_id=job.parent_job_id,
                kind="terminal",
                payload={"job_id": job_id, "status": "completed", "finished_at": _now_iso()},
            )
    except Exception as exc:  # noqa: BLE001
        _append_log(job_id, f"ERROR {exc!r}")
        upd(status="failed", error="ingest_failed", message=str(exc)[:500], finished_at=_now_iso())
        _publish_bus_event(
            job_id=job_id,
            parent_job_id=job.parent_job_id,
            kind="terminal",
            payload={
                "job_id": job_id,
                "status": "failed",
                "error": str(exc)[:500],
                "finished_at": _now_iso(),
            },
        )


def _run_ingest_thread(
    job_id: str,
    temp_path: Path,
    settings: Settings,
) -> None:
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
    for cid in children:
        ch = registry.get(cid)
        if ch:
            statuses.append(ch.status)
    failed = sum(1 for s in statuses if s == "failed")
    done = sum(1 for s in statuses if s in ("completed", "failed"))
    total = len(children)
    pct = int(100 * done / total) if total else 100
    if done < total:
        msg = f"Batch running ({done}/{total})"
        st = "running"
    elif failed == total:
        msg = f"Batch failed ({failed}/{total})"
        st = "failed"
    elif failed:
        ok = total - failed
        msg = f"Batch finished: {ok} ok, {failed} failed (of {total})"
        st = "completed"
    else:
        msg = f"Batch completed ({total} file(s))"
        st = "completed"
    registry._update(
        parent_id,
        status=st,
        message=msg,
        progress_current=pct,
        progress_total=100,
        finished_at=_now_iso() if done == total else parent.finished_at,
    )
    _publish_bus_event(
        job_id=parent_id,
        parent_job_id=None,
        kind="batch_progress",
        payload={
            "job_id": parent_id,
            "status": st,
            "message": msg,
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
            payload={"job_id": parent_id, "status": st, "finished_at": _now_iso()},
        )


def _run_batch_thread(
    parent_id: str, child_paths: list[tuple[str, Path]], settings: Settings
) -> None:
    registry = _registry(settings)
    parent = registry.get(parent_id)
    if not parent:
        for _, p in child_paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return
    registry._update(
        parent_id,
        status="running",
        message=f"Processing {len(child_paths)} file(s)…",
        progress_current=0,
        progress_total=100,
    )
    try:
        for cid, path in child_paths:
            _execute_single_ingest(cid, path, settings)
            _refresh_parent_job(parent_id)
    finally:
        for _, path in child_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        _refresh_parent_job(parent_id)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def start_batch_ingest_job(
    *,
    workspace_id: str,
    files: list[tuple[str, bytes]],
    settings: Settings,
) -> IngestJobRecord:
    """Sequential batch ingest; poll ``parent_job_id`` via ``GET /v1/ingest/jobs/{id}``."""

    if not files:
        raise HTTPException(status_code=400, detail="no_files")
    if len(files) > BATCH_MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail={"error": "too_many_files", "max": BATCH_MAX_FILES, "got": len(files)},
        )
    registry = _registry(settings)
    parent = registry.create_job(
        workspace_id,
        f"batch ({len(files)} files)",
        kind="batch_parent",
    )
    registry._update(
        parent.job_id,
        progress_total=len(files),
        message=f"Queued {len(files)} file(s)",
    )
    child_paths: list[tuple[str, Path]] = []
    for name, data in files:
        if not data:
            continue
        suffix = Path(name or "doc").suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            continue
        child = registry.create_job(
            workspace_id,
            (name or "upload").strip() or "upload",
            kind="batch_child",
            parent_job_id=parent.job_id,
        )
        safe = f"ingest-{child.job_id}{suffix}"
        temp_path = Path(gettempdir()) / safe
        temp_path.write_bytes(data)
        child_paths.append((child.job_id, temp_path))
        _append_log(child.job_id, f"Part of batch {parent.job_id}")
    if not child_paths:
        registry._update(
            parent.job_id,
            status="failed",
            error="no_valid_files",
            message="No supported files in batch",
            finished_at=_now_iso(),
        )
        raise HTTPException(status_code=400, detail="no_supported_files_in_batch")
    registry._update(parent.job_id, child_job_ids=[c[0] for c in child_paths])
    threading.Thread(
        target=_run_batch_thread,
        args=(parent.job_id, child_paths, settings),
        name=f"batch-{parent.job_id}",
        daemon=True,
    ).start()
    return parent


def start_ingest_job(
    *,
    workspace_id: str,
    filename: str,
    file_bytes: bytes,
    settings: Settings,
) -> IngestJobRecord:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="empty_file")

    suffix = Path(filename or "upload").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported_type_allowed:{','.join(sorted(SUPPORTED_SUFFIXES))}",
        )

    rec = _registry(settings).create_job(workspace_id, filename)
    safe_name = f"ingest-{rec.job_id}{suffix}"
    temp_path = Path(gettempdir()) / safe_name
    temp_path.write_bytes(file_bytes)
    _append_log(rec.job_id, f"Saved {len(file_bytes)} bytes → {temp_path.name}")

    thread = threading.Thread(
        target=_run_ingest_thread,
        args=(rec.job_id, temp_path, settings),
        name=f"ingest-{rec.job_id}",
        daemon=True,
    )
    thread.start()
    return rec


class IngestJobView(BaseModel):
    """JSON shape for ingest job polling."""

    job_id: str
    workspace_id: str
    filename: str
    status: str
    message: str = ""
    progress_current: int = 0
    progress_total: int = 100
    logs: str = ""
    work_id: str | None = None
    document_id: str | None = None
    skipped_duplicate: bool = False
    error: str | None = None
    created_at: str = ""
    finished_at: str | None = None
    kind: str = "single"
    parent_job_id: str | None = None
    child_job_ids: list[str] = Field(default_factory=list)
    stages: list["IngestStageView"] = Field(default_factory=list)
    phoenix_trace_id: str | None = None


class IngestStageView(BaseModel):
    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


def job_to_dict(rec: IngestJobRecord) -> dict[str, Any]:
    """Serialize a job record for JSON responses."""

    out = IngestJobView(
        job_id=rec.job_id,
        workspace_id=rec.workspace_id,
        filename=rec.filename,
        status=rec.status,
        message=rec.message,
        progress_current=rec.progress_current,
        progress_total=rec.progress_total,
        logs=rec.logs,
        work_id=rec.work_id,
        document_id=rec.document_id,
        skipped_duplicate=rec.skipped_duplicate,
        error=rec.error,
        created_at=rec.created_at,
        finished_at=rec.finished_at,
        kind=rec.kind,
        parent_job_id=rec.parent_job_id,
        child_job_ids=list(rec.child_job_ids),
        stages=[IngestStageView(**stage_row) for stage_row in rec.stages],
        phoenix_trace_id=rec.phoenix_trace_id,
    ).model_dump()
    if rec.kind == "batch_parent":
        child_jobs: list[dict[str, Any]] = []
        for cid in rec.child_job_ids:
            ch = _registry().get(cid)
            if ch:
                child_jobs.append(job_to_dict(ch))
        out["child_jobs"] = child_jobs
    return out


router = APIRouter(tags=["ingest"])


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str) -> dict[str, Any]:
    """Return status and logs for a workspace document ingest job."""

    registry = _registry()
    rec = registry.get(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="job_not_found")
    if rec.kind == "batch_parent":
        _refresh_parent_job(job_id)
        rec = registry.get(job_id) or rec
    return job_to_dict(rec)


def _parse_last_event_id(raw: str | None) -> int:
    if not raw:
        return 0
    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 0


def _is_terminal_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in {"completed", "failed"}


def _to_sse_event(seq: int, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(seq), "event": str(kind), "data": json.dumps(payload, ensure_ascii=True)}


async def _job_events_stream(job_id: str, request: Request) -> AsyncIterator[dict[str, Any]]:
    registry = _registry()
    rec = registry.get(job_id)
    if not rec:
        return
    yield _to_sse_event(0, "snapshot", {"job": job_to_dict(rec)})
    last_seq = _parse_last_event_id(request.headers.get("last-event-id"))
    if last_seq > 0:
        for seq, event in BUS.replay_from(job_id, last_seq):
            yield _to_sse_event(seq, event["kind"], event["payload"])
    async for seq, event in BUS.subscribe(job_id):
        if await request.is_disconnected():
            break
        yield _to_sse_event(seq, event["kind"], event["payload"])
        if event["kind"] == "terminal":
            break
        if rec.kind == "batch_parent" and event["kind"] == "batch_progress":
            refreshed = registry.get(job_id)
            if refreshed and _is_terminal_status(refreshed.status):
                break


@router.get("/ingest/jobs/{job_id}/events")
async def get_ingest_job_events(job_id: str, request: Request) -> EventSourceResponse:
    registry = _registry()
    rec = registry.get(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="job_not_found")
    if rec.kind == "batch_parent":
        _refresh_parent_job(job_id)
    return EventSourceResponse(
        _job_events_stream(job_id, request),
        ping=15,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


class IngestStubBody(BaseModel):
    """Unused body for legacy ``/ingest/arxiv`` and ``/ingest/doi`` stubs."""

    arxiv_id: str | None = None
    doi: str | None = None


@router.post("/ingest/arxiv")
def ingest_arxiv_stub(_body: IngestStubBody) -> dict[str, Any]:
    """Reserved: use workspace document upload instead."""

    raise HTTPException(
        status_code=501,
        detail="ingest_arxiv_not_implemented_upload_pdf_or_md",
    )


@router.post("/ingest/doi")
def ingest_doi_stub(_body: IngestStubBody) -> dict[str, Any]:
    """Reserved: use workspace document upload instead."""

    raise HTTPException(
        status_code=501,
        detail="ingest_doi_not_implemented_upload_pdf_or_md",
    )


@router.post("/ingest/pdf")
def ingest_pdf_stub() -> dict[str, Any]:
    """Reserved: multipart upload is under ``POST /v1/workspaces/{id}/ingest/document``."""

    raise HTTPException(
        status_code=501,
        detail="ingest_pdf_use_workspace_upload",
    )
