"""Throttled INFO for long non-VL ingest stages.

Stage boundaries log once per stage name when ``pipeline_log_heartbeat_run`` is active.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Iterator


def pipeline_log_heartbeat_interval_seconds() -> float:
    """Seconds between progress heartbeats.

    Env: ``SCIENCE_GRAPHRAG_INGEST_PIPELINE_LOG_HEARTBEAT_SECONDS``.
    """
    raw = os.getenv("SCIENCE_GRAPHRAG_INGEST_PIPELINE_LOG_HEARTBEAT_SECONDS", "60").strip()
    try:
        v = float(raw)
    except ValueError:
        return 60.0
    if v <= 0:
        return 60.0
    return v


@dataclass
class PipelineLogHeartbeatState:
    """Throttle state for pipeline stderr INFO lines."""

    last_progress_emit_monotonic: float = 0.0
    last_boundary_stage: str = field(default="")


_cv: ContextVar[PipelineLogHeartbeatState | None] = ContextVar(
    "science_graphrag_pipeline_log_hb", default=None
)


@contextmanager
def pipeline_log_heartbeat_run() -> Iterator[None]:
    """Activate pipeline logging context for one ingest run (job + DB stages)."""
    state = PipelineLogHeartbeatState()
    token = _cv.set(state)
    try:
        yield
    finally:
        _cv.reset(token)


def maybe_log_ingest_pipeline_stage_entry(logger: logging.Logger, *, stage_name: str) -> None:
    """Log once when entering a new pipeline stage (operator sees transitions)."""
    state = _cv.get()
    if state is None:
        return
    if stage_name == state.last_boundary_stage:
        return
    state.last_boundary_stage = stage_name
    state.last_progress_emit_monotonic = time.monotonic()
    logger.info(
        "Ingest pipeline stage=%s",
        stage_name,
        extra={"stage": "pipeline_stage_start"},
    )


def maybe_log_ingest_pipeline_progress_throttled(
    logger: logging.Logger, *, stage_name: str
) -> None:
    """Rate-limited INFO during a long stage (e.g. embed); counts / stage only."""
    state = _cv.get()
    if state is None:
        return
    now = time.monotonic()
    interval = pipeline_log_heartbeat_interval_seconds()
    if (now - state.last_progress_emit_monotonic) < interval:
        return
    state.last_progress_emit_monotonic = now
    logger.info(
        "Ingest pipeline progress stage=%s",
        stage_name,
        extra={"stage": "pipeline_progress_heartbeat"},
    )
