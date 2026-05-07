"""Plan mode tools (Epic P2.3) — session flag + SSE; enforcement in tool_execution_pipeline."""

from __future__ import annotations

import time
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.runtime_context import get_agent_graph_thread_id
from science_graphrag.config import Settings


class EnterPlanModeArgs(BaseModel):
    note: str = Field(
        default="",
        max_length=500,
        description="Optional short note recorded with plan mode state.",
    )


class ExitPlanModeArgs(BaseModel):
    approved: bool = Field(
        default=True,
        description="Whether the user approved leaving plan mode (recorded for audit only).",
    )


def build_plan_mode_tools(settings: Settings) -> list[BaseTool]:
    """Return ``enter_plan_mode`` / ``exit_plan_mode`` when feature flag is on."""
    if not settings.agent_plan_mode_tools_enabled:
        return []
    tools: list[BaseTool] = []

    @tool("enter_plan_mode", args_schema=EnterPlanModeArgs)
    def enter_plan_mode(note: str = "") -> dict[str, Any]:
        """Mark session as plan mode (read-focused); high-risk tools are denied until exit."""
        tid = get_agent_graph_thread_id()
        if not tid:
            return {
                "ok": False,
                "error": "missing_thread_id",
                "sse_hint": {"type": "plan_mode_error", "code": "missing_thread_id"},
            }
        payload = {
            "active": True,
            "entered_at": time.time(),
            "note": (note or "").strip()[:500],
        }
        get_session_memory_backend().patch_session_meta(tid, patch={"plan_mode": payload})
        return {
            "ok": True,
            "plan_mode": payload,
            "sse_hint": {"type": "plan_mode_entered", "note_len": len(payload["note"])},
        }

    @tool("exit_plan_mode", args_schema=ExitPlanModeArgs)
    def exit_plan_mode(approved: bool = True) -> dict[str, Any]:
        """Clear plan mode; restores normal tool policy."""
        tid = get_agent_graph_thread_id()
        if not tid:
            return {
                "ok": False,
                "error": "missing_thread_id",
                "sse_hint": {"type": "plan_mode_error", "code": "missing_thread_id"},
            }
        payload = {
            "active": False,
            "exited_at": time.time(),
            "approved": bool(approved),
        }
        get_session_memory_backend().patch_session_meta(tid, patch={"plan_mode": payload})
        return {
            "ok": True,
            "plan_mode": payload,
            "sse_hint": {"type": "plan_mode_exited", "approved": bool(approved)},
        }

    tools.extend([enter_plan_mode, exit_plan_mode])
    return tools
