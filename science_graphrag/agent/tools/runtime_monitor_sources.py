"""Resolve ``runtime_monitor_get`` snapshots from durable job stores (ingest, benchmarks).

In-process registry (``register_runtime_monitor_snapshot``) remains the highest-precedence
source inside ``runtime_monitor_surface`` for tests and explicit operator wiring.
"""

from __future__ import annotations

import logging
from typing import Any

from science_graphrag.config import Settings

logger = logging.getLogger(__name__)


def _ingest_job_to_snapshot(rec: Any) -> dict[str, Any]:
    """Map ``IngestJobRecord`` to unified monitor row."""
    from science_graphrag.api.ingest.dto import job_record_to_view

    view = job_record_to_view(rec)
    st = str(view.status or "").strip().lower()
    state = st if st in {"queued", "running", "completed", "failed"} else "unknown"
    pct = view.progress_pct
    progress: float | None
    if isinstance(pct, (int, float)):
        progress = max(0.0, min(1.0, float(pct)))
    else:
        tot = max(int(view.progress_total or 100), 1)
        cur = max(0, min(100, int(view.progress_current or 0)))
        progress = float(cur) / float(tot)
    err = (view.error or "").strip() or None
    degraded = bool(err or state == "failed" or bool(view.progress_indeterminate and state == "running"))
    last_hb = view.finished_at or view.created_at or None
    msg = str(view.message or "").strip()
    if err:
        err_tail: str | None = err[:800]
    elif state == "running" and (msg or view.active_stage):
        parts = [f"phase={view.ingest_phase}"]
        if view.active_stage:
            parts.append(f"stage={view.active_stage}")
        if view.detail_message:
            parts.append(str(view.detail_message)[:200])
        elif msg:
            parts.append(msg[:300])
        err_tail = " · ".join(parts)
    else:
        err_tail = None
    return {
        "state": state,
        "progress": progress,
        "last_heartbeat_at": last_hb,
        "degraded": degraded,
        "error_tail": err_tail,
        "source": "ingest",
        "timeout_hit": False,
    }


def _benchmark_summary_to_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    """Map ``task_store.get_run_summary`` dict to unified monitor row."""
    st = str(summary.get("status") or "").strip().lower()
    state = st if st in {"queued", "running", "completed", "failed", "cancelled"} else "unknown"
    prog = summary.get("progress") if isinstance(summary.get("progress"), dict) else {}
    try:
        total = max(int(prog.get("total") or 0), 0)
        done = max(int(prog.get("completed") or 0), 0)
        pct_raw = float(prog.get("percent") or 0.0)
    except (TypeError, ValueError):
        total, done, pct_raw = 0, 0, 0.0
    if total > 0:
        progress = max(0.0, min(1.0, float(done) / float(total)))
    else:
        progress = max(0.0, min(1.0, pct_raw / 100.0)) if pct_raw else None
    err = summary.get("error_message")
    err_s = str(err).strip() if err is not None else ""
    degraded = bool(err_s or state in {"failed", "cancelled"})
    last_hb = summary.get("completed_at") or summary.get("started_at") or summary.get("created_at")
    return {
        "state": state,
        "progress": progress,
        "last_heartbeat_at": str(last_hb) if last_hb else None,
        "degraded": degraded,
        "error_tail": err_s[:800] if err_s else None,
        "source": "benchmark",
        "timeout_hit": False,
    }


def resolve_runtime_monitor_from_job_stores(task_id: str, settings: Settings) -> dict[str, Any] | None:
    """Return a snapshot dict when ``task_id`` matches ingest or benchmark task store."""
    tid = (task_id or "").strip()
    if not tid:
        return None

    try:
        from science_graphrag.api.ingest.registry import _registry as ingest_registry_fn

        ingest_rec = ingest_registry_fn(settings).get_job(tid)
        if ingest_rec is not None:
            return _ingest_job_to_snapshot(ingest_rec)
    except Exception as exc:  # noqa: BLE001 — optional DB
        logger.debug("runtime_monitor ingest lookup failed: %s", exc)

    try:
        from science_graphrag.api.task_store import task_store

        bench = task_store.get_run_summary(tid)
        if isinstance(bench, dict) and str(bench.get("run_id") or "").strip() == tid:
            return _benchmark_summary_to_snapshot(bench)
    except Exception as exc:  # noqa: BLE001
        logger.debug("runtime_monitor benchmark lookup failed: %s", exc)

    return None
