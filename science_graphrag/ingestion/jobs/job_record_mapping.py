"""ORM ↔ ingest job DTO mapping helpers (keeps registry.py focused on persistence)."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.api.ingest.dto import IngestJobRecord, now_iso
from science_graphrag.ingestion.stage_context import IngestStage
from science_graphrag.storage.models_orm import IngestJobRecordOrm, IngestJobStageOrm


def single_job_progress_from_stages(
    stage_rows: list[dict[str, Any]],
    *,
    progress_total: int,
) -> tuple[int, int]:
    """Derive UI progress for single-document jobs from completed stage rows.

    ``progress_total`` seeds the UI denominator (clamped to at least 100).
    """
    stage_count = max(len(IngestStage), 1)
    completed = sum(1 for item in stage_rows if item.get("status") == "completed")
    p_total = max(progress_total, 100)
    p_current = int((completed / stage_count) * 100)
    return p_current, p_total


def ingest_job_stage_row_to_dict(
    row: IngestJobStageOrm, expected_duration_ms: int | None = None
) -> dict[str, Any]:
    """Serialize one ingest job stage ORM row to the API-facing stage dict."""
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
        except (json.JSONDecodeError, TypeError, ValueError):
            metrics = {}
    out: dict[str, Any] = {
        "name": row.stage,
        "status": row.status,
        "started_at": started_iso,
        "finished_at": finished_iso,
        "duration_ms": duration_ms,
        "metrics": metrics,
        "error": row.error,
    }
    dm = metrics.get("detail_message")
    if dm is not None and str(dm).strip():
        out["detail_message"] = str(dm).strip()[:500]
    for key in ("subprogress_current", "subprogress_total"):
        if key in metrics:
            try:
                v = int(metrics[key])
                if v >= 0:
                    out[key] = v
            except (TypeError, ValueError):
                pass
    if expected_duration_ms is not None:
        out["expected_duration_ms"] = int(expected_duration_ms)
    return out


def ingest_job_record_from_orm(
    row: IngestJobRecordOrm, stages: list[dict[str, Any]] | None = None
) -> IngestJobRecord:
    """Map a persisted ingest job row (+ optional stage rows) to ``IngestJobRecord``."""
    stage_rows = list(stages or [])
    progress_current = int(row.progress_current or 0)
    progress_total = int(row.progress_total or 100)
    if row.kind in ("single", "batch_child") and stage_rows:
        progress_current, progress_total = single_job_progress_from_stages(
            stage_rows,
            progress_total=progress_total,
        )
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
        queued_source_object_key=row.queued_source_object_key,
        queued_source_size=row.queued_source_size,
        queued_source_etag=row.queued_source_etag,
    )
