"""SQLAlchemy-backed ingest job registry."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from science_graphrag.config import Settings, get_settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobRecordOrm, IngestJobStageOrm

from .dto import IngestJobRecord, now_iso

_REGISTRY_LOCK = threading.Lock()
_REGISTRY_BOX: dict[str, IngestJobRegistry | None] = {"value": None}


def _registry(settings: Settings | None = None) -> "IngestJobRegistry":
    registry = _REGISTRY_BOX["value"]
    if registry is not None:
        return registry
    with _REGISTRY_LOCK:
        registry = _REGISTRY_BOX["value"]
        if registry is None:
            registry = IngestJobRegistry(settings or get_settings())
            _REGISTRY_BOX["value"] = registry
    return registry


class IngestJobRegistry:
    """Durable ingest job store backed by Postgres."""

    def __init__(self, settings: Settings) -> None:
        self.lock = threading.Lock()
        self._settings = settings
        self._engine = get_engine(settings.database_url)
        self._session_factory = session_factory(self._engine)
        self._bootstrapped = False

    def bootstrap(self) -> None:
        if self._bootstrapped:
            return
        with self.lock:
            if self._bootstrapped:
                return
            init_db(self._engine)
            self.mark_stale_running_jobs_failed()
            self._bootstrapped = True

    @staticmethod
    def _to_dataclass(
        row: IngestJobRecordOrm, stages: list[dict[str, Any]] | None = None
    ) -> IngestJobRecord:
        stage_rows = list(stages or [])
        progress_current = int(row.progress_current or 0)
        progress_total = int(row.progress_total or 100)
        if row.kind == "single" and stage_rows:
            stage_count = max(len(stage_rows), 1)
            try:
                from science_graphrag.ingestion.stage_context import IngestStage  # noqa: PLC0415

                stage_count = max(len(IngestStage), 1)
            except Exception:
                stage_count = max(len(stage_rows), 1)
            completed = sum(1 for item in stage_rows if item.get("status") == "completed")
            progress_total = max(progress_total, 100)
            progress_current = int((completed / stage_count) * 100)
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
            created_at=row.created_at.isoformat() if row.created_at else now_iso(),
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

    # Aliases for new module boundary nomenclature.
    def get_job(self, job_id: str) -> IngestJobRecord | None:
        return self.get(job_id)

    def list_jobs(self, workspace_id: str) -> list[IngestJobRecord]:
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
                return [
                    self._to_dataclass(row, stages=self._load_job_stages(session, row.job_id))
                    for row in rows
                ]

    def update_stage(self, job_id: str, *, status: str, message: str = "") -> None:
        payload: dict[str, Any] = {"status": status}
        if message:
            payload["message"] = message
        self._update(job_id, **payload)

    def mark_failed(self, job_id: str, *, error: str, message: str) -> None:
        self._update(job_id, status="failed", error=error, message=message, finished_at=now_iso())
