"""Background ingest jobs for workspace uploads (PDF / MD / TXT) with polling."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from tempfile import gettempdir
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.pipeline import SkippedDuplicateIngestError, ingest_document
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobRecordOrm
from science_graphrag.storage.neo4j_store import Neo4jGraphStore

SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})
BATCH_MAX_FILES = 200


def _append_log(job_id: str, line: str) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%S")
    chunk = f"[{ts}] {line}\n"
    with _REGISTRY.lock:
        with _REGISTRY._session_factory() as session:
            row = session.execute(
                select(IngestJobRecordOrm).where(IngestJobRecordOrm.job_id == str(job_id).strip()).limit(1)
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
    def _to_dataclass(row: IngestJobRecordOrm) -> IngestJobRecord:
        return IngestJobRecord(
            job_id=row.job_id,
            workspace_id=row.workspace_id,
            filename=row.filename,
            status=row.status,
            message=row.message or "",
            progress_current=int(row.progress_current or 0),
            progress_total=int(row.progress_total or 100),
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
        )

    def mark_stale_running_jobs_failed(self) -> None:
        with self.lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(IngestJobRecordOrm).where(IngestJobRecordOrm.status.in_(("queued", "running")))
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
                    select(IngestJobRecordOrm).where(IngestJobRecordOrm.job_id == str(job_id).strip()).limit(1)
                ).scalar_one_or_none()
                return self._to_dataclass(row) if row else None

    def _update(self, job_id: str, **kwargs: Any) -> None:
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm).where(IngestJobRecordOrm.job_id == str(job_id).strip()).limit(1)
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


_REGISTRY = IngestJobRegistry(get_settings())


def _ingest_workspace_tag(workspace_id: str) -> list[str]:
    w = workspace_id.strip()
    return [w] if w else []


def _execute_single_ingest(job_id: str, temp_path: Path, settings: Settings) -> None:
    job = _REGISTRY.get(job_id)
    if not job:
        return

    def upd(**kwargs: Any) -> None:
        _REGISTRY._update(job_id, **kwargs)

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
            return

        upd(message="Running pipeline (Neo4j / vectors / SQL)…", progress_current=15)

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
                    )
        except SkippedDuplicateIngestError as dup:
            skipped = True
            doc_id = dup.document_id
            work_id = None
            _append_log(
                job_id, f"Skipped duplicate sha256={dup.sha256} document_id={dup.document_id}"
            )

        upd(progress_current=85, message="Attaching to workspace…")
        store = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            ws = store.workspace_get(job.workspace_id)
            if not ws:
                upd(
                    status="failed",
                    error="workspace_not_found",
                    message="Workspace not found",
                    finished_at=_now_iso(),
                )
                return
            if work_id and not skipped:
                if not store.workspace_add_work(job.workspace_id, str(work_id)):
                    upd(
                        status="failed",
                        error="work_attach_failed",
                        message="Ingest OK but could not attach work to workspace (invalid work_id?)",
                        document_id=doc_id,
                        work_id=work_id,
                        finished_at=_now_iso(),
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
    except Exception as exc:  # noqa: BLE001
        _append_log(job_id, f"ERROR {exc!r}")
        upd(status="failed", error="ingest_failed", message=str(exc)[:500], finished_at=_now_iso())


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
    parent = _REGISTRY.get(parent_id)
    if not parent or parent.kind != "batch_parent":
        return
    children = [cid for cid in parent.child_job_ids if cid]
    if not children:
        return
    statuses = []
    for cid in children:
        ch = _REGISTRY.get(cid)
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
    _REGISTRY._update(
        parent_id,
        status=st,
        message=msg,
        progress_current=pct,
        progress_total=100,
        finished_at=_now_iso() if done == total else parent.finished_at,
    )


def _run_batch_thread(parent_id: str, child_paths: list[tuple[str, Path]], settings: Settings) -> None:
    parent = _REGISTRY.get(parent_id)
    if not parent:
        for _, p in child_paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return
    _REGISTRY._update(
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
    parent = _REGISTRY.create_job(
        workspace_id,
        f"batch ({len(files)} files)",
        kind="batch_parent",
    )
    _REGISTRY._update(
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
        child = _REGISTRY.create_job(
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
        _REGISTRY._update(
            parent.job_id,
            status="failed",
            error="no_valid_files",
            message="No supported files in batch",
            finished_at=_now_iso(),
        )
        raise HTTPException(status_code=400, detail="no_supported_files_in_batch")
    _REGISTRY._update(parent.job_id, child_job_ids=[c[0] for c in child_paths])
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

    rec = _REGISTRY.create_job(workspace_id, filename)
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
    ).model_dump()
    if rec.kind == "batch_parent":
        child_jobs: list[dict[str, Any]] = []
        for cid in rec.child_job_ids:
            ch = _REGISTRY.get(cid)
            if ch:
                child_jobs.append(job_to_dict(ch))
        out["child_jobs"] = child_jobs
    return out


router = APIRouter(tags=["ingest"])


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str) -> dict[str, Any]:
    """Return status and logs for a workspace document ingest job."""

    rec = _REGISTRY.get(job_id)
    if not rec:
        raise HTTPException(status_code=404, detail="job_not_found")
    if rec.kind == "batch_parent":
        _refresh_parent_job(job_id)
        rec = _REGISTRY.get(job_id) or rec
    return job_to_dict(rec)


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
