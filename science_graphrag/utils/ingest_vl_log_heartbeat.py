"""Rate-limited INFO logs for long VL PDF ingest (counts only; no paths or document text)."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field


def vl_log_heartbeat_interval_seconds() -> float:
    """Minimum seconds between throttled VL progress INFO lines (default 60)."""
    raw = os.getenv("SCIENCE_GRAPHRAG_INGEST_VL_LOG_HEARTBEAT_SECONDS", "60").strip()
    try:
        v = float(raw)
    except ValueError:
        return 60.0
    if v <= 0:
        return 60.0
    return v


@dataclass
class VlLogHeartbeatState:
    """Mutable throttle state for one ingest PDF parse."""

    last_emit_monotonic: float = 0.0
    started_logged: bool = field(default=False)


def maybe_log_vl_parse_started(
    logger: logging.Logger,
    state: VlLogHeartbeatState,
    *,
    batch_count: int,
    page_total: int,
    batch_size: int,
) -> None:
    """One INFO line when VL batching is known (not throttled)."""
    if state.started_logged:
        return
    state.started_logged = True
    logger.info(
        "VL PDF parse started: batches=%s pages=%s batch_size=%s",
        int(batch_count),
        int(page_total),
        int(batch_size),
        extra={"stage": "vl_pdf_start"},
    )


def maybe_log_vl_page_heartbeat(
    logger: logging.Logger,
    state: VlLogHeartbeatState,
    *,
    pages_done: int,
    pages_total: int,
    now_monotonic: float | None = None,
) -> None:
    """Throttled INFO for steady-state VL progress (counts only)."""
    now = time.monotonic() if now_monotonic is None else float(now_monotonic)
    interval = vl_log_heartbeat_interval_seconds()
    if (now - state.last_emit_monotonic) < interval:
        return
    state.last_emit_monotonic = now
    logger.info(
        "VL PDF progress: pages=%s/%s",
        int(pages_done),
        int(pages_total),
        extra={"stage": "vl_pdf_heartbeat"},
    )
