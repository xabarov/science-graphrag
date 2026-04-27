"""Rolling ingest stage duration stats for WX2-BE ``expected_duration_ms`` hints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from science_graphrag.storage.models_orm import IngestJobRecordOrm, IngestJobStageOrm

# When no history exists for a stage name, UI still needs a sane weight (ms).
DEFAULT_STAGE_WEIGHT_MS = 120_000


def load_mean_stage_duration_ms(session: Session, *, max_jobs: int = 30) -> dict[str, int]:
    """Mean ``duration_ms`` per stage name over the last ``max_jobs`` completed single jobs."""

    subq = (
        select(IngestJobRecordOrm.job_id)
        .where(
            IngestJobRecordOrm.status == "completed",
            IngestJobRecordOrm.kind == "single",
        )
        .order_by(IngestJobRecordOrm.finished_at.desc().nulls_last())
        .limit(max(1, min(max_jobs, 200)))
        .subquery()
    )
    stmt = (
        select(
            IngestJobStageOrm.stage,
            func.avg(
                func.extract(
                    "epoch",
                    IngestJobStageOrm.finished_at - IngestJobStageOrm.started_at,
                )
                * 1000
            ).label("avg_ms"),
        )
        .where(IngestJobStageOrm.job_id.in_(select(subq.c.job_id)))
        .where(IngestJobStageOrm.status == "completed")
        .where(IngestJobStageOrm.started_at.isnot(None))
        .where(IngestJobStageOrm.finished_at.isnot(None))
        .group_by(IngestJobStageOrm.stage)
    )
    out: dict[str, int] = {}
    for stage_name, avg_ms in session.execute(stmt).all():
        key = str(stage_name or "").strip()
        if not key or avg_ms is None:
            continue
        try:
            ms = int(float(avg_ms))
        except (TypeError, ValueError):
            continue
        if ms > 0:
            out[key] = max(1000, min(ms, 3_600_000))  # clamp 1s .. 1h per stage
    return out


def compute_weighted_progress_pct(
    stages: list[dict[str, Any]], weights: Mapping[str, int]
) -> float | None:
    """Return 0..1 weighted progress; running stages count as half weight."""

    if not stages:
        return None
    total = 0.0
    done = 0.0
    for row in stages:
        name = str(row.get("name") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        w = float(weights.get(name, DEFAULT_STAGE_WEIGHT_MS))
        if w <= 0:
            w = float(DEFAULT_STAGE_WEIGHT_MS)
        total += w
        if status == "completed":
            done += w
        elif status == "running":
            done += 0.5 * w
    if total <= 0:
        return None
    return max(0.0, min(1.0, done / total))


def compute_weighted_progress_pct_with_running_fraction(
    stages: list[dict[str, Any]],
    weights: Mapping[str, int],
    *,
    running_intra_fraction: float | None,
) -> float | None:
    """
    Like ``compute_weighted_progress_pct``, but the first ``running`` stage uses
    ``running_intra_fraction`` (0..1) when provided instead of a fixed 0.5 weight.
    """

    if not stages:
        return None
    total = 0.0
    done = 0.0
    running_applied = False
    for row in stages:
        name = str(row.get("name") or "").strip()
        status = str(row.get("status") or "").strip().lower()
        w = float(weights.get(name, DEFAULT_STAGE_WEIGHT_MS))
        if w <= 0:
            w = float(DEFAULT_STAGE_WEIGHT_MS)
        total += w
        if status == "completed":
            done += w
        elif status == "running":
            if not running_applied and running_intra_fraction is not None:
                frac = max(0.0, min(1.0, float(running_intra_fraction)))
                running_applied = True
            else:
                frac = 0.5
            done += frac * w
    if total <= 0:
        return None
    return max(0.0, min(1.0, done / total))
