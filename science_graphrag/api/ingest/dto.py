"""DTO and data records for ingest jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from science_graphrag.api.ingest.ingest_progress import canonical_progress_fields_for_job
from science_graphrag.ingestion.stage_stats import compute_weighted_progress_pct


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class IngestJobRecord:
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
    created_at: str = field(default_factory=now_iso)
    finished_at: str | None = None
    kind: str = "single"
    parent_job_id: str | None = None
    child_job_ids: list[str] = field(default_factory=list)
    stages: list[dict[str, Any]] = field(default_factory=list)
    phoenix_trace_id: str | None = None
    progress_pct: float | None = None
    queued_source_object_key: str | None = None
    queued_source_size: int | None = None
    queued_source_etag: str | None = None


class IngestStageView(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    expected_duration_ms: int | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    detail_message: str | None = None
    subprogress_current: int | None = None
    subprogress_total: int | None = None


class IngestJobEvent(BaseModel):
    job_id: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    source_job_id: str | None = None


class IngestJobView(BaseModel):
    """JSON shape for ingest job polling."""

    model_config = ConfigDict(extra="ignore")

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
    stages: list[IngestStageView] = Field(default_factory=list)
    phoenix_trace_id: str | None = None
    progress_pct: float | None = None
    ingest_phase: str = "preparing_document"
    active_stage: str = ""
    detail_message: str | None = None
    subprogress_current: int | None = None
    subprogress_total: int | None = None
    progress_indeterminate: bool = Field(
        default=False,
        description="True when overall percent is not meaningful (e.g. single VL batch in flight).",
    )
    pending_conflicts: dict[str, int] = Field(
        default_factory=lambda: {"works": 0, "authors": 0, "entities": 0},
        description=(
            "Pending dedup conflicts with origin=ingest for this job's work_id (by queue kind)."
        ),
    )
    pending_conflicts_count: int = Field(
        default=0,
        description="Sum of pending_conflicts values (backward compatible aggregate).",
    )


def job_record_to_view(rec: IngestJobRecord) -> IngestJobView:
    stage_rows: list[dict[str, Any]] = [dict(x) for x in rec.stages]
    weights: dict[str, int] = {}
    for row in stage_rows:
        name = str(row.get("name") or "").strip()
        exp = row.get("expected_duration_ms")
        if name and exp is not None:
            try:
                weights[name] = max(1000, int(exp))
            except (TypeError, ValueError):
                pass
    pct_legacy: float | None = None
    if rec.kind in ("single", "batch_child") and stage_rows:
        pct_legacy = compute_weighted_progress_pct(stage_rows, weights)

    canon = canonical_progress_fields_for_job(
        kind=str(rec.kind or "single"),
        status=rec.status,
        message=rec.message,
        progress_current=rec.progress_current,
        progress_total=rec.progress_total,
        stages=stage_rows,
        weights=weights,
    )
    pct_final = canon.get("progress_pct")
    if pct_final is None:
        pct_final = pct_legacy

    if rec.kind == "batch_parent":
        pct_final = None
        canon = {
            "ingest_phase": "preparing_document",
            "active_stage": "",
            "detail_message": None,
            "subprogress_current": None,
            "subprogress_total": None,
            "progress_indeterminate": False,
        }

    return IngestJobView(
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
        stages=[IngestStageView(**stage_row) for stage_row in stage_rows],
        phoenix_trace_id=rec.phoenix_trace_id,
        progress_pct=pct_final,
        ingest_phase=str(canon.get("ingest_phase") or "preparing_document"),
        active_stage=str(canon.get("active_stage") or ""),
        detail_message=canon.get("detail_message"),
        subprogress_current=canon.get("subprogress_current"),
        subprogress_total=canon.get("subprogress_total"),
        progress_indeterminate=bool(canon.get("progress_indeterminate")),
        pending_conflicts={"works": 0, "authors": 0, "entities": 0},
        pending_conflicts_count=0,
    )
