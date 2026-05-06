"""In-process runtime task snapshots for ``runtime_monitor_get``.

Production wiring can replace the global registry; tests register rows explicitly.
"""

from __future__ import annotations

import threading
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

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
            payload = {
                "ok": True,
                "task_id": tid,
                "state": "unknown",
                "progress": None,
                "last_heartbeat_at": None,
                "degraded": True,
                "error_tail": None,
                "detail": "no_snapshot_registered",
                "sse_hint": _monitor_hint(task_id=tid, state="unknown", degraded=True, ok=True),
            }
            return payload
        tail = row.get("error_tail")
        max_tail = int(settings.agent_runtime_monitor_max_error_tail_chars)
        if isinstance(tail, str) and len(tail) > max_tail:
            tail = tail[:max_tail] + "...[truncated]"
        out = {
            "ok": True,
            "task_id": tid,
            "state": str(row.get("state") or "unknown"),
            "progress": row.get("progress"),
            "last_heartbeat_at": row.get("last_heartbeat_at"),
            "degraded": bool(row.get("degraded", False)),
            "error_tail": tail,
            "sse_hint": _monitor_hint(
                task_id=tid,
                state=str(row.get("state") or "unknown"),
                degraded=bool(row.get("degraded", False)),
                ok=True,
            ),
        }
        return out

    return [runtime_monitor_get]
