"""Environment, sys.path bootstrap, and trace-review timing helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from .orchestrator_paths import REPO_ROOT, SCRIPT_DIR


def runtime_attribution_from_env() -> tuple[str | None, str | None]:
    runtime = str(os.environ.get("SCIENCE_GRAPHRAG_AGENT_RUNTIME") or "").strip()
    if runtime in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if runtime == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    if runtime == "langgraph_supervisor_v3":
        return "supervisor_specialists_v3", "supervisor_graph_v3"
    return None, None


def runtime_attribution_from_runtime_id(runtime_id: Any) -> tuple[str | None, str | None]:
    rt = str(runtime_id or "").strip()
    if rt in {"retrieval_v1", "langgraph_research_v1"}:
        return "single_agent_research", "single_agent_react"
    if rt == "langgraph_supervisor_v1":
        return "supervisor_specialists", "supervisor_graph"
    if rt == "langgraph_supervisor_v3":
        return "supervisor_specialists_v3", "supervisor_graph_v3"
    return None, None


def ensure_local_imports() -> None:
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    eval_root = REPO_ROOT / "eval"
    if str(eval_root) not in sys.path:
        sys.path.insert(0, str(eval_root))


def load_dotenv(env_file: Path) -> None:
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
    )

    load_dotenv_or_warn(env_file)


def trace_review_heartbeat_interval_s() -> float:
    raw = (os.environ.get("AGENT_LIVE_TRACE_REVIEW_HEARTBEAT_SEC") or "").strip()
    if not raw:
        return 60.0
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 60.0


def compaction_in_turn_heartbeat_sec(*, mode: str, override: float | None = None) -> float:
    """Interval for stderr heartbeats during blocking ``/v2/agent/query`` waits.

    Focused long-thread lane defaults to a tighter cadence so operators see progress
    under slow turns without waiting for the generic compaction review default.
    """
    if override is not None:
        return max(5.0, float(override))
    mode_s = str(mode or "").strip()
    if mode_s == "focused_long_thread":
        raw = (
            os.environ.get("AGENT_LIVE_COMPACTION_FOCUS_HEARTBEAT_SEC")
            or os.environ.get("AGENT_LIVE_COMPACTION_REVIEW_HEARTBEAT_SEC")
            or "15"
        ).strip()
    else:
        raw = (os.environ.get("AGENT_LIVE_COMPACTION_REVIEW_HEARTBEAT_SEC") or "30").strip()
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 15.0 if mode_s == "focused_long_thread" else 30.0


def e2e_subprocess_timeout_sec() -> float | None:
    """Optional hard cap for OD E2E subprocess (unset = no extra cap beyond OS)."""
    raw = (os.environ.get("AGENT_LIVE_E2E_SUBPROCESS_TIMEOUT_SEC") or "").strip()
    if not raw:
        return None
    try:
        return max(60.0, float(raw))
    except ValueError:
        return None
