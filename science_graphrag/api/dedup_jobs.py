"""Background jobs for Wave L dedup scans (process-local registry, same pattern as ingest jobs)."""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import Settings
from science_graphrag.dedup.author_dedup_engine import run_author_dedup_scan
from science_graphrag.dedup.work_dedup_engine import run_work_dedup_scan
from science_graphrag.storage.db import init_db


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
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.jobs: dict[str, DedupJobRecord] = {}

    def create(self, *, workspace_id: str, kind: str) -> DedupJobRecord:
        jid = str(uuid.uuid4())
        rec = DedupJobRecord(job_id=jid, workspace_id=workspace_id, kind=kind, status="queued")
        with self.lock:
            self.jobs[jid] = rec
        return rec

    def get(self, job_id: str) -> DedupJobRecord | None:
        with self.lock:
            return self.jobs.get(job_id)

    def _upd(self, job_id: str, **kwargs: Any) -> None:
        with self.lock:
            rec = self.jobs.get(job_id)
            if not rec:
                return
            for k, v in kwargs.items():
                setattr(rec, k, v)


_REGISTRY = DedupJobRegistry()


def get_dedup_job(job_id: str) -> DedupJobRecord | None:
    return _REGISTRY.get(job_id)


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
    rec = _REGISTRY.get(job_id)
    if not rec:
        return
    _REGISTRY._upd(job_id, status="running", message="Scanning works…")

    def upd(**kwargs: Any) -> None:
        _REGISTRY._upd(job_id, **kwargs)

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        init_db(engine)
        factory = sessionmaker(bind=engine)
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
    rec = _REGISTRY.get(job_id)
    if not rec:
        return
    _REGISTRY._upd(job_id, status="running", message="Scanning authors…")

    def upd(**kwargs: Any) -> None:
        _REGISTRY._upd(job_id, **kwargs)

    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        init_db(engine)
        factory = sessionmaker(bind=engine)
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
    rec = _REGISTRY.create(workspace_id=workspace_id, kind="work_scan")
    t = threading.Thread(target=_run_work_scan, args=(rec.job_id, settings), daemon=True)
    t.start()
    return rec


def start_author_dedup_scan_job(*, workspace_id: str, settings: Settings) -> DedupJobRecord:
    rec = _REGISTRY.create(workspace_id=workspace_id, kind="author_scan")
    t = threading.Thread(target=_run_author_scan, args=(rec.job_id, settings), daemon=True)
    t.start()
    return rec
