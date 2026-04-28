"""Prometheus metrics for ingest (optional; gated by Settings.metrics_enabled)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    from science_graphrag.config import Settings

INGEST_JOBS_STARTED = Counter(
    "ingest_jobs_started_total",
    "Ingest jobs claimed and entering the pipeline",
    ("kind",),
)

INGEST_JOBS_TERMINAL = Counter(
    "ingest_jobs_terminal_total",
    "Ingest jobs reaching terminal actor state",
    ("kind", "status"),
)

INGEST_JOB_DURATION = Histogram(
    "ingest_job_duration_seconds",
    "Wall time from successful claim to pipeline finish in the worker",
    ("kind",),
)

INGEST_STAGE_DURATION = Histogram(
    "ingest_stage_duration_seconds",
    "Wall time for one ingest stage (enter to completed or failed)",
    ("stage", "status"),
)


def observe_ingest_job_started(settings: "Settings", kind: str) -> None:
    """Increment started counter when metrics are enabled."""
    if not getattr(settings, "metrics_enabled", False):
        return
    INGEST_JOBS_STARTED.labels(kind=kind or "unknown").inc()


def observe_ingest_job_terminal(
    settings: "Settings",
    *,
    kind: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Increment terminal counter and observe pipeline duration when metrics are enabled."""
    if not getattr(settings, "metrics_enabled", False):
        return
    k = kind or "unknown"
    st = (status or "unknown").strip() or "unknown"
    INGEST_JOBS_TERMINAL.labels(kind=k, status=st).inc()
    INGEST_JOB_DURATION.labels(kind=k).observe(max(0.0, float(duration_seconds)))


def observe_ingest_stage_finished(
    settings: "Settings",
    *,
    stage: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record per-stage wall time when metrics are enabled (low-cardinality stage names)."""
    if not getattr(settings, "metrics_enabled", False):
        return
    st = (stage or "unknown").strip() or "unknown"
    raw_status = (status or "unknown").strip().lower() or "unknown"
    if raw_status not in {"completed", "failed"}:
        raw_status = "unknown"
    INGEST_STAGE_DURATION.labels(stage=st, status=raw_status).observe(
        max(0.0, float(duration_seconds)),
    )
