"""Bounded worktree isolation tools (Epic P1.1) — session-scoped sandbox directories."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.runtime_context import get_agent_graph_thread_id
from science_graphrag.config import Settings


def _safe_rmtree_under_worktree_root(path_str: str, root: Path) -> bool:
    """Remove a directory only if it resolves to a strict subdirectory of ``root``."""
    raw = (path_str or "").strip()
    if not raw:
        return False
    try:
        rp = Path(raw).resolve()
        rroot = root.expanduser().resolve()
    except OSError:
        return False
    if rp == rroot:
        return False
    try:
        rp.relative_to(rroot)
    except ValueError:
        return False
    if not rp.is_dir():
        return False
    shutil.rmtree(rp, ignore_errors=True)
    return True


def _sanitize_label(raw: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "_", (raw or "").strip())[:64]
    return s or "default"


def _worktree_state(tid: str) -> dict[str, Any] | None:
    ent = get_session_memory_backend().get_session_copy(tid)
    if not isinstance(ent, dict):
        return None
    meta = ent.get("session_meta") or {}
    if not isinstance(meta, dict):
        return None
    wt = meta.get("agent_worktree")
    return wt if isinstance(wt, dict) else None


def _resolved_sandbox_path(settings: Settings, tid: str, label: str) -> Path:
    root = Path(settings.agent_worktree_base_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    safe_tid = re.sub(r"[^a-zA-Z0-9._-]+", "_", tid.strip())[:128]
    sub = (root / safe_tid / _sanitize_label(label)).resolve()
    try:
        sub.relative_to(root)
    except ValueError as exc:
        raise ValueError("worktree path escapes sandbox root") from exc
    return sub


class EnterWorktreeArgs(BaseModel):
    """Arguments for creating or re-entering a bounded sandbox directory."""

    label: str = Field(
        default="default",
        min_length=1,
        max_length=64,
        description="Short label for this worktree (alphanumeric, dot, dash, underscore).",
    )


class ExitWorktreeArgs(BaseModel):
    """Arguments for leaving worktree mode and optionally cleaning the sandbox."""

    remove_files: bool = Field(
        default=True,
        description="When true, delete the sandbox directory tree on exit.",
    )


def build_worktree_isolation_tools(settings: Settings) -> list[BaseTool]:
    """Return ``enter_worktree`` / ``exit_worktree`` when feature flag is on."""
    if not settings.agent_worktree_tools_enabled:
        return []
    tools: list[BaseTool] = []

    @tool("enter_worktree", args_schema=EnterWorktreeArgs)
    def enter_worktree(label: str = "default") -> dict[str, Any]:
        """Create or re-enter a per-thread sandbox directory under ``agent_worktree_base_dir``."""
        tid = get_agent_graph_thread_id()
        if not tid:
            return {
                "ok": False,
                "error": "missing_thread_id",
                "sse_hint": {"type": "worktree_error", "code": "missing_thread_id"},
            }
        prior = _worktree_state(tid)
        if isinstance(prior, dict) and prior.get("active") and prior.get("path"):
            prev_path = str(prior.get("path") or "").strip()
            prev_label = _sanitize_label(str(prior.get("label") or "default"))
            requested_label = _sanitize_label(label)
            if prev_path and Path(prev_path).is_dir() and prev_label == requested_label:
                return {
                    "ok": True,
                    "reused": True,
                    "path": prior.get("path"),
                    "label": prior.get("label"),
                    "sse_hint": {
                        "type": "worktree_entered",
                        "label": str(prior.get("label") or ""),
                        "path": str(prior.get("path") or ""),
                    },
                }
        try:
            target = _resolved_sandbox_path(settings, tid, label)
        except ValueError as exc:
            return {
                "ok": False,
                "error": "invalid_path",
                "detail": str(exc),
                "sse_hint": {"type": "worktree_error", "code": "invalid_path"},
            }
        target.mkdir(parents=True, exist_ok=True)
        payload = {
            "active": True,
            "path": str(target),
            "label": _sanitize_label(label),
            "entered_at": time.time(),
        }
        get_session_memory_backend().patch_session_meta(tid, patch={"agent_worktree": payload})
        return {
            "ok": True,
            "path": str(target),
            "label": payload["label"],
            "sse_hint": {
                "type": "worktree_entered",
                "label": payload["label"],
                "path": str(target),
            },
        }

    @tool("exit_worktree", args_schema=ExitWorktreeArgs)
    def exit_worktree(remove_files: bool = True) -> dict[str, Any]:
        """Leave worktree mode and optionally delete the sandbox directory."""
        tid = get_agent_graph_thread_id()
        if not tid:
            return {
                "ok": False,
                "error": "missing_thread_id",
                "sse_hint": {"type": "worktree_error", "code": "missing_thread_id"},
            }
        prior = _worktree_state(tid)
        path_str = str((prior or {}).get("path") or "").strip()
        removed = False
        if remove_files and path_str:
            root = Path(settings.agent_worktree_base_dir)
            removed = _safe_rmtree_under_worktree_root(path_str, root)
        get_session_memory_backend().patch_session_meta(
            tid,
            patch={"agent_worktree": {"active": False, "exited_at": time.time(), "path": None}},
        )
        return {
            "ok": True,
            "removed_sandbox": removed,
            "previous_path": path_str or None,
            "sse_hint": {"type": "worktree_exited", "removed": removed},
        }

    tools.extend([enter_worktree, exit_worktree])
    return tools
