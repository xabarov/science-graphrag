"""Unified LangGraph tool execution seam (Wave 3 + Phase 6 deadline).

Thin wrapper around LangGraph ``ToolNode``: normalize names, enforce an optional
mode/tool-policy allowlist, emit lightweight debug events, optionally append
JSONL sidechain transcripts for specialist branches, and (Phase 6 of the
2026-05-07 orchestration stabilization plan) cap each tool batch with an
independent wall-clock deadline so a single stuck tool/LLM call does not eat
the global ``agent_step_timeout_seconds``.
"""

from __future__ import annotations

import functools
import json
import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

# When the per-tool deadline fires, surface the failure as a ToolMessage with
# this stable error code. Callers (planner, salvage) can pattern-match on it.
PER_TOOL_DEADLINE_REASON = "per_tool_deadline_exceeded"

from science_graphrag.agent.can_use_tool_contract import CanUseTool
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.debug_streamable_types import TOOL_SSE_HINT_STREAMABLE_TYPES
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.runtime_context import agent_graph_thread_id_scope
from science_graphrag.agent.sidechain_paths import (
    sidechain_transcripts_enabled,
    sidechain_transcripts_root,
)
from science_graphrag.agent.tool_call_normalization import (
    normalize_tool_call_name,
    state_with_normalized_last_ai_tool_calls,
)
from science_graphrag.agent.tool_use_summary import apply_tool_use_summary_to_tool_json_content
from science_graphrag.config import Settings

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _plan_mode_high_risk_tool_names() -> frozenset[str]:
    """Tools with manifest risk ``high`` are blocked while plan_mode is active."""
    from science_graphrag.agent.tool_manifest import manifest_by_name

    return frozenset(n for n, e in manifest_by_name().items() if e.risk == "high")


def _session_plan_mode_active(thread_id: str) -> bool:
    ent = get_session_memory_backend().get_session_copy(thread_id)
    meta = ent.get("session_meta") or {}
    if not isinstance(meta, dict):
        return False
    pm = meta.get("plan_mode")
    if not isinstance(pm, dict):
        return False
    return bool(pm.get("active"))


def _thread_id_for_tool_context(st: AgentState) -> str | None:
    tid = st.get("thread_id")
    if isinstance(tid, str) and tid.strip():
        return tid.strip()
    meta = st.get("metadata")
    if isinstance(meta, dict):
        mt = meta.get("thread_id")
        if isinstance(mt, str) and mt.strip():
            return mt.strip()
    return None


_SIDECHAIN_LOCK = threading.Lock()


def _sidechain_jsonl_path(settings: Settings, sidechain_id: str) -> Path:
    root = sidechain_transcripts_root(settings)
    return root / f"{sidechain_id}.jsonl"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as a single line (JSONL)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    try:
        with _SIDECHAIN_LOCK:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
    except OSError as exc:
        logger.warning("tool_execution_pipeline: skip sidechain append (path=%s): %s", path, exc)


def _per_tool_deadline_seconds(settings: Settings) -> float:
    """Return the configured per-tool-call deadline (0 disables the cap)."""
    raw = float(getattr(settings, "agent_per_tool_call_timeout_seconds", 0.0) or 0.0)
    if raw <= 0.0:
        return 0.0
    return min(raw, 600.0)


def _run_with_per_tool_deadline(
    runner: Callable[[], Any], *, deadline_s: float
) -> tuple[Any | None, bool]:
    """Run ``runner`` in a daemon thread with a wall-clock cap.

    Returns ``(result, fired)``. When ``fired`` is True the worker thread is
    abandoned (left running as daemon) and ``result`` is None — the caller
    must synthesize a fallback ToolMessage so the rest of the turn proceeds.

    A ``ThreadPoolExecutor`` is **not** suitable here: its ``__exit__`` calls
    ``shutdown(wait=True)`` which blocks the supervisor until the stuck tool
    actually returns, defeating the deadline. A bare daemon thread does not
    pin process exit and lets the agent turn move on immediately.
    """
    result_holder: list[Any] = []
    error_holder: list[BaseException] = []

    def _worker_target() -> None:
        try:
            result_holder.append(runner())
        except BaseException as exc:  # pylint: disable=broad-except
            error_holder.append(exc)

    worker = threading.Thread(target=_worker_target, name="tool-batch-deadline", daemon=True)
    worker.start()
    worker.join(timeout=deadline_s)
    if worker.is_alive():
        return None, True
    if error_holder:
        raise error_holder[0]
    return (result_holder[0] if result_holder else None), False


def _build_per_tool_deadline_messages(*, tcs: list[Any], deadline_s: float) -> list[ToolMessage]:
    """Synthesize ToolMessage failures when the batch deadline fires."""
    out: list[ToolMessage] = []
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        call_id = tc.get("id")
        payload = {
            "ok": False,
            "error": PER_TOOL_DEADLINE_REASON,
            "reason": (
                f"per-tool wall-clock cap of {deadline_s:.1f}s exceeded; "
                "tool call abandoned to keep the turn alive"
            ),
            "tool": nm,
            "deadline_seconds": float(deadline_s),
        }
        out.append(
            ToolMessage(
                content=json.dumps(payload, ensure_ascii=False),
                tool_call_id=str(call_id or ""),
                name=nm,
            )
        )
    return out


def effective_tool_policy(state: AgentState) -> str:
    """Return coordinator tool_policy for this graph state (defaults to allow_tools)."""
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy")
    if isinstance(tp, dict):
        pol = str(tp.get("tool_policy") or "").strip()
        if pol in {"no_tools", "clarify", "allow_tools"}:
            return pol
    return "allow_tools"


def effective_mode_key(*, settings: Settings, state: AgentState) -> str:
    """Mode key for allowlist matrix."""
    rt = str(settings.agent_runtime or "").strip()
    if rt == "langgraph_research_v1":
        return "single_agent_react"
    if rt in ("langgraph_supervisor_v1", "langgraph_supervisor_v3"):
        spec = str(state.get("current_specialist") or "").strip()
        if spec:
            return f"supervisor:{spec}"
        return "supervisor:unknown"
    return rt or "unknown"


def apply_allowed_tools_matrix(
    tools: list[BaseTool],
    *,
    settings: Settings,
    state: AgentState,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Filter tool objects by mode + tool policy (optional)."""
    if not settings.agent_allowed_tools_matrix_enabled:
        return tools, {"skipped": True}

    mode = effective_mode_key(settings=settings, state=state)
    pol = effective_tool_policy(state)
    names = {
        "mode": mode,
        "tool_policy": pol,
        "before": len(tools),
        "denylist_hits": [],
        "removed": [],
    }

    deny = set(settings.agent_tool_denylist_always or [])
    mode_deny = (settings.agent_tool_denylist_by_mode or {}).get(mode) or []
    deny.update(str(x).strip() for x in mode_deny if str(x).strip())

    policy_map = settings.agent_tool_allowlist_by_tool_policy or {}
    allow_for_policy = policy_map.get(pol)

    out: list[BaseTool] = []
    for t in tools:
        n = normalize_tool_call_name(getattr(t, "name", "") or "")
        if not n:
            continue
        if n in deny:
            names["denylist_hits"].append(n)
            names["removed"].append({"tool": n, "reason": "denylist"})
            continue
        if isinstance(allow_for_policy, list) and allow_for_policy:
            allowed = {normalize_tool_call_name(x) for x in allow_for_policy if str(x).strip()}
            if n not in allowed:
                names["removed"].append({"tool": n, "reason": f"policy_allowlist:{pol}"})
                continue
        out.append(t)

    names["after"] = len(out)
    return out, names


def _react_bound_tool_names_from_state(state: AgentState) -> set[str] | None:
    """Optional per-turn bound tool surface for single-agent ReAct (shortlist vs ToolNode)."""
    meta = state.get("metadata") or {}
    raw = meta.get("react_bound_tool_names")
    if not isinstance(raw, list) or not raw:
        return None
    out = {normalize_tool_call_name(str(x)) for x in raw if str(x).strip()}
    return out or None


def _deny_maps_for_ai_tool_calls(
    *,
    policy: str,
    tcs: list[Any],
    allowed_names: set[str],
) -> dict[str, str]:
    """Compute permission denials for the pending tool_calls batch."""
    denies: dict[str, str] = {}
    if policy in {"no_tools", "clarify"}:
        for tc in tcs:
            if not isinstance(tc, dict):
                continue
            nm = normalize_tool_call_name(str(tc.get("name") or ""))
            if nm:
                denies[nm] = f"tool_policy:{policy}"

    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        if not nm:
            continue
        if nm not in allowed_names and nm not in denies:
            denies[nm] = "not_in_bound_tool_surface"
    return denies


def _permission_denial_messages_from_ai(
    tcs: list[Any], *, denies: dict[str, str]
) -> list[ToolMessage]:
    """Construct ToolMessages that explain permission_denied without executing tools."""
    out_msgs: list[ToolMessage] = []
    for tc in tcs:
        if not isinstance(tc, dict):
            continue
        nm = normalize_tool_call_name(str(tc.get("name") or ""))
        call_id = tc.get("id")
        reason = denies.get(nm)
        if not reason:
            continue
        payload = {"ok": False, "error": "permission_denied", "reason": reason, "tool": nm}
        out_msgs.append(
            ToolMessage(
                content=json.dumps(payload, ensure_ascii=False),
                tool_call_id=str(call_id or ""),
                name=nm,
            )
        )
    return out_msgs


def build_tool_execution_node(
    *,
    tools: list[BaseTool],
    settings: Settings,
    sidechain_id: str | None = None,
    can_use_tool: CanUseTool | None = None,
) -> Callable[[AgentState, Any | None], dict[str, Any]]:
    """Return LangGraph node callable with validate/permission/hooks around ToolNode."""
    inner = ToolNode(tools)

    def tools_node(state: AgentState, config: Any | None = None) -> dict[str, Any]:
        """Execute tool calls for the latest AIMessage with explicit stages + sidechain logs."""
        st0 = state_with_normalized_last_ai_tool_calls(state)
        policy = effective_tool_policy(st0)
        msgs = list(st0.get("messages") or [])
        last = msgs[-1] if msgs else None

        events: list[dict[str, Any]] = []
        if not isinstance(last, AIMessage):
            events.append(
                {
                    "type": "tool_execution",
                    "phase": "validate",
                    "ok": False,
                    "code": "no_ai_message",
                }
            )
            return {"debug_events": events}

        tcs = getattr(last, "tool_calls", None) or []
        if not tcs:
            events.append(
                {
                    "type": "tool_execution",
                    "phase": "validate",
                    "ok": False,
                    "code": "no_tool_calls",
                }
            )
            return {"debug_events": events}

        allowed_names = {normalize_tool_call_name(getattr(t, "name", "") or "") for t in tools}

        denies = _deny_maps_for_ai_tool_calls(policy=policy, tcs=tcs, allowed_names=allowed_names)

        bound = _react_bound_tool_names_from_state(st0)
        if bound:
            for tc in tcs:
                if not isinstance(tc, dict):
                    continue
                nm = normalize_tool_call_name(str(tc.get("name") or ""))
                if nm and nm not in bound and nm not in denies:
                    denies[nm] = "not_in_bound_tool_surface"

        tid_plan = _thread_id_for_tool_context(st0)
        if tid_plan and _session_plan_mode_active(tid_plan):
            hi = _plan_mode_high_risk_tool_names()
            for tc in tcs:
                if not isinstance(tc, dict):
                    continue
                nm = normalize_tool_call_name(str(tc.get("name") or ""))
                if nm and nm in hi and nm not in denies:
                    denies[nm] = "plan_mode:high_risk_tool_blocked"

        if can_use_tool is not None:
            for tc in tcs:
                if not isinstance(tc, dict):
                    continue
                nm = normalize_tool_call_name(str(tc.get("name") or ""))
                if not nm or nm in denies:
                    continue
                try:
                    reason = can_use_tool(st0, nm, tc)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    denies[nm] = f"can_use_tool_callback_error:{type(exc).__name__}"
                else:
                    if reason:
                        denies[nm] = str(reason).strip() or "tool_denied_by_policy"

        if denies:
            # Permission phase — synthesize ToolMessage errors without invoking tools.
            out_msgs = _permission_denial_messages_from_ai(tcs, denies=denies)
            events.append(
                {
                    "type": "tool_execution",
                    "phase": "permission",
                    "ok": False,
                    "denied": [{"tool": k, "reason": v} for k, v in denies.items()],
                }
            )
            return {"messages": out_msgs, "debug_events": events}

        # Pre-hook (trace)
        pre_ts = time.time()
        tool_names = [
            normalize_tool_call_name(str(tc.get("name") or ""))
            for tc in tcs
            if isinstance(tc, dict)
        ]
        events.append(
            {
                "type": "tool_execution",
                "phase": "pre_hooks",
                "ok": True,
                "tools": [n for n in tool_names if n],
            }
        )

        sidechain_path: Path | None = None
        if sidechain_transcripts_enabled(settings) and sidechain_id:
            sidechain_path = _sidechain_jsonl_path(settings, sidechain_id)
            _append_jsonl(
                sidechain_path,
                {
                    "ts": pre_ts,
                    "event": "tool_batch_start",
                    "tools": [n for n in tool_names if n],
                    "tool_policy": policy,
                },
            )

        tid_ctx = _thread_id_for_tool_context(st0)
        deadline_s = _per_tool_deadline_seconds(settings)
        deadline_fired = False

        def _run_inner() -> Any:
            with agent_graph_thread_id_scope(tid_ctx):
                if config is None:
                    return inner.invoke(st0)
                return inner.invoke(st0, config)

        if deadline_s > 0.0:
            inner_out, deadline_fired = _run_with_per_tool_deadline(
                _run_inner, deadline_s=deadline_s
            )
            if deadline_fired:
                inner_out = {
                    "messages": _build_per_tool_deadline_messages(
                        tcs=list(tcs), deadline_s=deadline_s
                    )
                }
        else:
            inner_out = _run_inner()

        post_ts = time.time()
        if deadline_fired:
            events.append(
                {
                    "type": "tool_execution",
                    "phase": "deadline",
                    "ok": False,
                    "code": PER_TOOL_DEADLINE_REASON,
                    "deadline_seconds": float(deadline_s),
                }
            )
        events.append(
            {
                "type": "tool_execution",
                "phase": "post_hooks",
                "ok": True,
                "elapsed_ms": int(max(0.0, (post_ts - pre_ts)) * 1000),
            }
        )

        if sidechain_path is not None:
            _append_jsonl(
                sidechain_path,
                {
                    "ts": post_ts,
                    "event": "tool_batch_end",
                    "elapsed_ms": int(max(0.0, (post_ts - pre_ts)) * 1000),
                },
            )

        extra_sse: list[dict[str, Any]] = []
        out_msgs2: list[Any] = []
        if isinstance(inner_out, dict) and isinstance(inner_out.get("messages"), list):
            out_msgs2 = list(inner_out.get("messages") or [])
        elif isinstance(inner_out, list):
            out_msgs2 = list(inner_out)
        summary_rows: list[dict[str, Any]] = []
        for m in out_msgs2:
            if not isinstance(m, ToolMessage):
                continue
            nm = normalize_tool_call_name(str(getattr(m, "name", "") or ""))
            raw = getattr(m, "content", None)
            if isinstance(raw, str):
                new_raw, meta = apply_tool_use_summary_to_tool_json_content(
                    settings=settings, tool_name=nm, content=raw
                )
                if meta is not None:
                    m.content = new_raw
                    summary_rows.append(meta)
            try:
                body = json.loads(str(m.content or ""))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if not isinstance(body, dict):
                continue
            hint = body.get("sse_hint")
            if (
                isinstance(hint, dict)
                and str(hint.get("type") or "") in TOOL_SSE_HINT_STREAMABLE_TYPES
            ):
                extra_sse.append({k: v for k, v in hint.items() if v is not None})
        if summary_rows:
            events.append(
                {
                    "type": "tool_use_summary_batch",
                    "ok": True,
                    "count": len(summary_rows),
                    "rows": summary_rows[:32],
                }
            )
        events.extend(extra_sse)

        if isinstance(inner_out, dict) and isinstance(inner_out.get("messages"), list):
            return {**inner_out, "debug_events": events}
        return {"messages": inner_out, "debug_events": events}

    return tools_node
