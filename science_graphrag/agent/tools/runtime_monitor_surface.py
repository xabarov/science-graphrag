"""In-process runtime task snapshots for ``runtime_monitor_get``.

Production wiring can replace the global registry; tests register rows explicitly.
"""

from __future__ import annotations

import threading
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.runtime_monitor_sources import (
    resolve_runtime_monitor_from_job_stores,
)
from science_graphrag.config import Settings

_REGISTRY_LOCK = threading.Lock()
_TASK_STATUS: dict[str, dict[str, Any]] = {}


def register_runtime_monitor_snapshot(task_id: str, snapshot: dict[str, Any]) -> None:
    """Test / integration hook: upsert a task status row."""
    tid = (task_id or "").strip()
    if not tid:
        return
    with _REGISTRY_LOCK:
        _TASK_STATUS[tid] = dict(snapshot)


def clear_runtime_monitor_snapshots_for_tests() -> None:
    with _REGISTRY_LOCK:
        _TASK_STATUS.clear()


def _monitor_hint(**kwargs: Any) -> dict[str, Any]:
    """SSE/debug payload for monitor lookups (stable keys for telemetry + trace-review)."""

    return {"type": "runtime_monitor", **{k: v for k, v in kwargs.items() if v is not None}}


class RuntimeMonitorArgs(BaseModel):
    task_id: str = Field(..., min_length=1, description="Logical async task identifier.")


def build_runtime_monitor_tools(settings: Settings) -> list[BaseTool]:
    if not settings.agent_runtime_monitor_tool_enabled:
        return []

    @tool("runtime_monitor_get", args_schema=RuntimeMonitorArgs)
    def runtime_monitor_get(task_id: str) -> dict[str, Any]:
        """Return unified status contract for a long-running task snapshot."""
        tid = (task_id or "").strip()
        if not tid:
            return {
                "ok": False,
                "error": "empty_task_id",
                "sse_hint": _monitor_hint(ok=False),
            }
        with _REGISTRY_LOCK:
            row = dict(_TASK_STATUS.get(tid) or {})
        if not row:
            row = resolve_runtime_monitor_from_job_stores(tid, settings) or {}
        if not row:
            payload = {
                "ok": True,
                "task_id": tid,
                "state": "unknown",
                "progress": None,
                "last_heartbeat_at": None,
                "degraded": True,
                "error_tail": None,
                "detail": "no_snapshot_registered",
                "source": None,
                "timeout_hit": None,
                "sse_hint": _monitor_hint(
                    task_id=tid,
                    state="unknown",
                    degraded=True,
                    ok=True,
                    source=None,
                ),
            }
            return payload
        if row.get("source") is None:
            row["source"] = "explicit"
        tail = row.get("error_tail")
        max_tail = int(settings.agent_runtime_monitor_max_error_tail_chars)
        if isinstance(tail, str) and len(tail) > max_tail:
            tail = tail[:max_tail] + "...[truncated]"
        state_s = str(row.get("state") or "unknown")
        deg = bool(row.get("degraded", False))
        to_hit = row.get("timeout_hit")
        timeout_hit = bool(to_hit) if to_hit is not None else None
        src = row.get("source")
        source = str(src) if src is not None else None
        out = {
            "ok": True,
            "task_id": tid,
            "state": state_s,
            "progress": row.get("progress"),
            "last_heartbeat_at": row.get("last_heartbeat_at"),
            "degraded": deg,
            "error_tail": tail,
            "source": source,
            "timeout_hit": timeout_hit,
            "sse_hint": _monitor_hint(
                task_id=tid,
                state=state_s,
                degraded=deg,
                ok=True,
                source=source,
                timeout_hit=timeout_hit,
            ),
        }
        return out

    return [runtime_monitor_get]
