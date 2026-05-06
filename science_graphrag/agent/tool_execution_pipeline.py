"""Unified LangGraph tool execution seam (Wave 3).

Thin wrapper around LangGraph ``ToolNode``: normalize names, enforce an optional
mode/tool-policy allowlist, emit lightweight debug events, and optionally append
JSONL sidechain transcripts for specialist branches.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.can_use_tool_contract import CanUseTool
from science_graphrag.agent.debug_streamable_types import TOOL_SSE_HINT_STREAMABLE_TYPES
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.runtime_context import agent_graph_thread_id_scope
from science_graphrag.agent.tool_call_normalization import (
    normalize_tool_call_name,
    state_with_normalized_last_ai_tool_calls,
)
from science_graphrag.config import Settings


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
    root = Path(settings.agent_sidechain_transcripts_dir or ".agent_sidechains").expanduser()
    return root / f"{sidechain_id}.jsonl"


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    """Append one JSON object as a single line (JSONL)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, default=str)
    with _SIDECHAIN_LOCK:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


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
        if settings.agent_sidechain_transcripts_enabled and sidechain_id:
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
        with agent_graph_thread_id_scope(tid_ctx):
            if config is None:
                inner_out = inner.invoke(st0)
            else:
                inner_out = inner.invoke(st0, config)

        post_ts = time.time()
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
        for m in out_msgs2:
            if not isinstance(m, ToolMessage):
                continue
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
        events.extend(extra_sse)

        if isinstance(inner_out, dict) and isinstance(inner_out.get("messages"), list):
            return {**inner_out, "debug_events": events}
        return {"messages": inner_out, "debug_events": events}

    return tools_node
