"""SQLAlchemy-backed ingest job registry."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text

from science_graphrag.api.ingest.dto import IngestJobRecord, now_iso
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.jobs.job_record_mapping import (
    ingest_job_record_from_orm,
    ingest_job_stage_row_to_dict,
)
from science_graphrag.ingestion.stage_stats import load_mean_stage_duration_ms
from science_graphrag.storage.db import (
    dispose_engine_for_database_url,
    get_engine,
    init_db,
    session_factory,
)
from science_graphrag.storage.models_orm import IngestJobRecordOrm, IngestJobStageOrm

_REGISTRY_LOCK = threading.Lock()
_REGISTRY_BOX: dict[str, IngestJobRegistry | None] = {"value": None}


def reset_ingest_job_registry_for_tests() -> None:
    """Clear the process-global ingest registry and dispose its SQLAlchemy engine cache entry.

    Tests that swap ``Settings.database_url`` must call this (or rely on
    :func:`get_ingest_job_registry` URL mismatch handling) to avoid cross-test leakage.
    """
    with _REGISTRY_LOCK:
        old = _REGISTRY_BOX["value"]
        _REGISTRY_BOX["value"] = None
    if old is not None:
        dispose_engine_for_database_url(old.resolved_database_url)


def get_ingest_job_registry(settings: Settings | None = None) -> "IngestJobRegistry":
    """Return the process-global registry bound to ``settings.database_url``.

    If the resolved DSN changes vs the currently cached registry, the previous registry's
    engine is disposed and a new :class:`IngestJobRegistry` is constructed.
    """
    resolved = settings or get_settings()
    url = str(resolved.database_url).strip()
    stale: IngestJobRegistry | None = None
    with _REGISTRY_LOCK:
        existing = _REGISTRY_BOX["value"]
        if existing is not None and existing.resolved_database_url != url:
            stale = existing
            _REGISTRY_BOX["value"] = None
    if stale is not None:
        dispose_engine_for_database_url(stale.resolved_database_url)
    with _REGISTRY_LOCK:
        if _REGISTRY_BOX["value"] is None:
            _REGISTRY_BOX["value"] = IngestJobRegistry(resolved)
        return _REGISTRY_BOX["value"]


def _registry(settings: Settings | None = None) -> "IngestJobRegistry":
    """Backward-compatible alias for :func:`get_ingest_job_registry`."""
    return get_ingest_job_registry(settings)


class IngestJobRegistry:
    """Durable ingest job store backed by Postgres."""

    def __init__(self, settings: Settings) -> None:
        self.lock = threading.Lock()
        self._settings = settings
        self._engine = get_engine(settings.database_url)
        self._session_factory = session_factory(self._engine)
        self._bootstrapped = False

    @property
    def resolved_database_url(self) -> str:
        """Normalized DSN key used for registry swap / engine disposal."""
        return str(self._settings.database_url).strip()

    @property
    def job_session_factory(self) -> Callable[..., Any]:
        """Public SQLAlchemy session factory for ingest job rows and stage timelines."""
        return self._session_factory

    def bootstrap(self) -> None:
        """Create DB tables if needed (idempotent)."""
        if self._bootstrapped:
            return
        with self.lock:
            if self._bootstrapped:
                return
            init_db(self._engine)
            self._bootstrapped = True

    def _to_dataclass(
        self, row: IngestJobRecordOrm, stages: list[dict[str, Any]] | None = None
    ) -> IngestJobRecord:
        return ingest_job_record_from_orm(row, stages)

    def _stage_to_dict(
        self, row: IngestJobStageOrm, expected_duration_ms: int | None = None
    ) -> dict[str, Any]:
        return ingest_job_stage_row_to_dict(row, expected_duration_ms)

    def _load_job_stages(
        self,
        session: Any,
        job_id: str,
        *,
        stage_stats: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        stats = stage_stats if stage_stats is not None else load_mean_stage_duration_ms(session)
        stage_rows = (
            session.execute(
                select(IngestJobStageOrm)
                .where(IngestJobStageOrm.job_id == str(job_id).strip())
                .order_by(IngestJobStageOrm.started_at.asc(), IngestJobStageOrm.stage.asc())
            )
            .scalars()
            .all()
        )
        return [
            self._stage_to_dict(row, stats.get(str(row.stage or "").strip()) or None)
            for row in stage_rows
        ]

    def mark_stale_running_jobs_failed(self) -> None:
        """Mark queued/running jobs as failed after API restart."""
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
        """Insert a new ingest job row and return its DTO."""
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
        """Load job by id including stage rows."""
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return None
                stats = load_mean_stage_duration_ms(session)
                stages = self._load_job_stages(session, job_id, stage_stats=stats)
                return self._to_dataclass(row, stages=stages)

    def claim_queued_job(self, job_id: str) -> bool:
        """Atomically set queued job status to running and return claim result."""
        with self.lock:
            with self._session_factory() as session:
                result = session.execute(
                    text(
                        "UPDATE ingest_jobs SET status='running' "
                        "WHERE job_id=:job_id AND status='queued' "
                        "RETURNING job_id"
                    ),
                    {"job_id": str(job_id).strip()},
                )
                claimed = result.fetchone() is not None
                session.commit()
        return claimed

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        """Apply partial field updates to a job row."""
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return
                for key, value in kwargs.items():
                    if key == "created_at":
                        continue
                    if key == "finished_at":
                        row.finished_at = (
                            datetime.fromisoformat(value)
                            if isinstance(value, str) and value
                            else value
                        )
                        continue
                    if key == "child_job_ids":
                        row.child_job_ids = [str(x) for x in (value or []) if x]
                        continue
                    setattr(row, key, value)
                session.commit()

    def append_job_log_line(self, job_id: str, line: str) -> None:
        """Append a timestamped line to the job log (truncated server-side)."""
        chunk = f"[{now_iso()[11:19]}] {line}\n"
        with self.lock:
            with self._session_factory() as session:
                row = session.execute(
                    select(IngestJobRecordOrm)
                    .where(IngestJobRecordOrm.job_id == str(job_id).strip())
                    .limit(1)
                ).scalar_one_or_none()
                if not row:
                    return
                row.logs = ((row.logs or "") + chunk)[-48_000:]
                session.commit()

    # Aliases for new module boundary nomenclature.
    def get_job(self, job_id: str) -> IngestJobRecord | None:
        """Alias for :meth:`get` (job id including stages)."""
        return self.get(job_id)

    def list_jobs(self, workspace_id: str) -> list[IngestJobRecord]:
        """List jobs for a workspace, newest first, each with stage rows."""
        with self.lock:
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(IngestJobRecordOrm)
                        .where(IngestJobRecordOrm.workspace_id == workspace_id)
                        .order_by(IngestJobRecordOrm.created_at.desc())
                    )
                    .scalars()
                    .all()
                )
                stats = load_mean_stage_duration_ms(session)
                return [
                    self._to_dataclass(
                        row,
                        stages=self._load_job_stages(session, row.job_id, stage_stats=stats),
                    )
                    for row in rows
                ]

    def reset_stale_running_jobs_to_queued(self, *, before: datetime) -> list[str]:
        """Turn orphan ``running`` rows into ``queued`` so the worker can claim them again.

        If the Dramatiq message was dropped (AgeLimit, OOM) or the process died, the DB can
        stay ``running`` while ``ingest_document_actor`` refuses to touch ``running`` jobs.
        """
        job_ids: list[str] = []
        with self.lock:
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(IngestJobRecordOrm).where(
                            IngestJobRecordOrm.status == "running",
                            IngestJobRecordOrm.created_at < before,
                        )
                    )
                    .scalars()
                    .all()
                )
                for row in rows:
                    row.status = "queued"
                    row.message = "Re-queued after stale running recovery (worker restart)"
                    row.error = None
                    row.finished_at = None
                    job_ids.append(str(row.job_id))
                if job_ids:
                    session.commit()
        return job_ids

    def list_stale_queued_jobs(self, *, before: datetime) -> list[IngestJobRecord]:
        """Return queued jobs older than ``before`` (compensation sweep)."""
        with self.lock:
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(IngestJobRecordOrm)
                        .where(
                            IngestJobRecordOrm.status == "queued",
                            IngestJobRecordOrm.created_at < before,
                        )
                        .order_by(IngestJobRecordOrm.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                stats = load_mean_stage_duration_ms(session)
                return [
                    self._to_dataclass(
                        row,
                        stages=self._load_job_stages(session, row.job_id, stage_stats=stats),
                    )
                    for row in rows
                ]

    def update_stage(self, job_id: str, *, status: str, message: str = "") -> None:
        """Update job status (and optional message) for coarse worker progress."""
        payload: dict[str, Any] = {"status": status}
        if message:
            payload["message"] = message
        self.update_job(job_id, **payload)

    def mark_failed(self, job_id: str, *, error: str, message: str) -> None:
        """Set terminal failed state with error code and user-facing message."""
        self.update_job(
            job_id, status="failed", error=error, message=message, finished_at=now_iso()
        )
