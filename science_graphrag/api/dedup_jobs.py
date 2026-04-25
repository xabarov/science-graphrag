"""Background jobs for Wave L dedup scans (process-local registry, same pattern as ingest jobs)."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from science_graphrag.config import Settings, get_settings
from science_graphrag.dedup.author_dedup_engine import run_author_dedup_scan
from science_graphrag.dedup.work_dedup_engine import run_work_dedup_scan
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import DedupJobRecordOrm

_REGISTRY_LOCK = threading.Lock()
_REGISTRY_BOX: dict[str, DedupJobRegistry | None] = {"value": None}


def _registry(settings: Settings | None = None):
    registry = _REGISTRY_BOX["value"]
    if registry is not None:
        return registry
    with _REGISTRY_LOCK:
        registry = _REGISTRY_BOX["value"]
        if registry is None:
            registry = DedupJobRegistry(settings or get_settings())
            _REGISTRY_BOX["value"] = registry
    return registry


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class DedupJobRecord:
    job_id: str
    workspace_id: str
    kind: str  # work_scan | author_scan
    status: str
    message: str = ""
    conflicts_inserted: int = 0
    error: str | None = None
    finished_at: str | None = None
    created_at: str = field(default_factory=_now_iso)


class DedupJobRegistry:
    def __init__(self, settings: Settings) -> None:
        self.lock = threading.Lock()
        self._engine = get_engine(settings.database_url)
        init_db(self._engine)
        self._session_factory = session_factory(self._engine)
        self.mark_stale_running_jobs_failed()

    @staticmethod
    def _to_dataclass(row: DedupJobRecordOrm) -> DedupJobRecord:
        return DedupJobRecord(
            job_id=row.job_id,
            workspace_id=row.workspace_id,
            kind=row.kind,
            status=row.status,
            message=row.message or "",
            conflicts_inserted=int(row.conflicts_inserted or 0),
            error=row.error,
            finished_at=row.finished_at.isoformat() if row.finished_at else None,
            created_at=row.created_at.isoformat() if row.created_at else _now_iso(),
        )

    def mark_stale_running_jobs_failed(self) -> None:
        with self.lock:
            with self._session_factory() as session:
                rows = session.execute(
                    select(DedupJobRecordOrm).where(
                        DedupJobRecordOrm.status.in_(("queued", "running"))
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

    def create(self, *, workspace_id: str, kind: str) -> DedupJobRecord:
        jid = str(uuid.uuid4())
        with self.lock:
            with self._session_factory() as session:
                row = DedupJobRecordOrm(
                    job_id=jid,
                    workspace_id=workspace_id,
                    kind=kind,
                    status="queued",
                    message="Queued",
                )
                session.add(row)
                session.commit()
                session.refresh(row)
                return self._to_dataclass(row)

    def get(self, job_id: str) -> DedupJobRecord | None:
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(DedupJobRecordOrm)
                    .where(DedupJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                return self._to_dataclass(row) if row else None

    def update(self, job_id: str, **kwargs: Any) -> None:
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(DedupJobRecordOrm)
                    .where(DedupJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return
                for k, v in kwargs.items():
                    if k == "finished_at":
                        row.finished_at = (
                            datetime.fromisoformat(v) if isinstance(v, str) and v else v
                        )
                    else:
                        setattr(row, k, v)
                session.commit()


def get_dedup_job(job_id: str) -> DedupJobRecord | None:
    return _registry().get(job_id)


def dedup_job_to_dict(rec: DedupJobRecord) -> dict[str, Any]:
    return {
        "job_id": rec.job_id,
        "workspace_id": rec.workspace_id,
        "kind": rec.kind,
        "status": rec.status,
        "message": rec.message,
        "conflicts_inserted": rec.conflicts_inserted,
        "error": rec.error,
        "finished_at": rec.finished_at,
        "created_at": rec.created_at,
    }


def _run_work_scan(job_id: str, settings: Settings) -> None:
    registry = _registry(settings)
    rec = registry.get(job_id)
    if not rec:
        return
    registry.update(job_id, status="running", message="Scanning works…")

    def upd(**kwargs: Any) -> None:
        registry.update(job_id, **kwargs)

    try:
        engine = get_engine(settings.database_url)
        init_db(engine)
        factory = session_factory(engine)
        with factory() as session:
            n = run_work_dedup_scan(
                settings=settings,
                workspace_id=rec.workspace_id,
                session=session,
            )
        upd(
            status="completed",
            message=f"Inserted {n} new conflict(s)",
            conflicts_inserted=n,
            finished_at=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        upd(
            status="failed",
            error=str(exc)[:500],
            message="dedup_scan_failed",
            finished_at=_now_iso(),
        )


def _run_author_scan(job_id: str, settings: Settings) -> None:
    registry = _registry(settings)
    rec = registry.get(job_id)
    if not rec:
        return
    registry.update(job_id, status="running", message="Scanning authors…")

    def upd(**kwargs: Any) -> None:
        registry.update(job_id, **kwargs)

    try:
        engine = get_engine(settings.database_url)
        init_db(engine)
        factory = session_factory(engine)
        with factory() as session:
            n = run_author_dedup_scan(
                settings=settings,
                workspace_id=rec.workspace_id,
                session=session,
            )
        upd(
            status="completed",
            message=f"Inserted {n} new author conflict(s)",
            conflicts_inserted=n,
            finished_at=_now_iso(),
        )
    except Exception as exc:  # noqa: BLE001
        upd(
            status="failed",
            error=str(exc)[:500],
            message="author_dedup_scan_failed",
            finished_at=_now_iso(),
        )


def start_work_dedup_scan_job(*, workspace_id: str, settings: Settings) -> DedupJobRecord:
    rec = _registry(settings).create(workspace_id=workspace_id, kind="work_scan")
    t = threading.Thread(target=_run_work_scan, args=(rec.job_id, settings), daemon=True)
    t.start()
    return rec


def start_author_dedup_scan_job(*, workspace_id: str, settings: Settings) -> DedupJobRecord:
    rec = _registry(settings).create(workspace_id=workspace_id, kind="author_scan")
    t = threading.Thread(target=_run_author_scan, args=(rec.job_id, settings), daemon=True)
    t.start()
    return rec
