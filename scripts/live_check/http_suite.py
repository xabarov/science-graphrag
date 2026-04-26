"""Reusable HTTP checks for a running science-graphrag API (agent v2).

Used by ``scripts/live_check/agent_v2_http.py`` and optional pytest under ``tests/live/``.

Operator notes (env vars, CH4 gate): see ``scripts/live_check/README.md``.
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx


@dataclass
class CheckResult:
    """Single named check outcome."""

    name: str
    ok: bool
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def _extra_headers() -> dict[str, str]:
    """Optional auth headers from the operator environment."""
    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def check_health(client: httpx.Client, base: str) -> CheckResult:
    """GET ``/health``."""
    url = f"{base.rstrip('/')}/health"
    try:
        r = client.get(url)
        r.raise_for_status()
        body = r.json()
    except Exception as exc:  # noqa: BLE001
        return CheckResult("health", False, str(exc))
    return CheckResult("health", True, "ok", {"body": body})


def check_agent_v2_sync_json(
    client: httpx.Client,
    base: str,
    *,
    workspace_id: str | None,
    question: str,
    thread_id: str | None = None,
    history_digest: list[dict[str, str]] | None = None,
) -> CheckResult:
    """POST ``/v2/agent/query`` with ``Accept: application/json``."""
    url = f"{base.rstrip('/')}/v2/agent/query"
    payload: dict[str, Any] = {"question": question}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if thread_id:
        payload["thread_id"] = thread_id
    if history_digest is not None:
        payload["history_digest"] = history_digest
    try:
        r = client.post(
            url,
            json=payload,
            headers={"Accept": "application/json", **_extra_headers()},
        )
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as exc:
        return CheckResult(
            "agent_v2_sync_json",
            False,
            f"HTTP {exc.response.status_code}: {exc.response.text[:500]}",
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("agent_v2_sync_json", False, str(exc))

    issues: list[str] = []
    if not isinstance(data.get("answer"), str) or not str(data["answer"]).strip():
        issues.append("empty_or_missing_answer")
    if "tool_trace" not in data:
        issues.append("missing_tool_trace")
    if "run_metadata" not in data:
        issues.append("missing_run_metadata")
    if thread_id and data.get("thread_id") != thread_id:
        issues.append(f"thread_id_mismatch expected={thread_id!r} got={data.get('thread_id')!r}")

    trace = data.get("tool_trace") or []
    tool_names = [x.get("tool") for x in trace if isinstance(x, dict)]

    if thread_id and os.environ.get("AGENT_LIVE_GATE_CH4", "").strip() in ("1", "true", "yes"):
        if "session_init" not in tool_names:
            issues.append("missing_session_init_in_tool_trace")
        rm = data.get("run_metadata") or {}
        comp = rm.get("compaction") if isinstance(rm, dict) else None
        if not isinstance(comp, dict) or "kinds" not in comp:
            issues.append("missing_compaction_in_run_metadata")

    ok = not issues

    return CheckResult(
        "agent_v2_sync_json",
        ok,
        "; ".join(issues) if issues else "ok",
        {
            "duration_ms": data.get("duration_ms"),
            "warnings": data.get("warnings"),
            "tools": tool_names,
            "answer_class": data.get("answer_class"),
        },
    )


def _parse_sse_lines(lines: Iterable[str | bytes]) -> list[dict[str, Any]]:
    """Parse ``data:`` JSON lines from an SSE body fragment."""
    events: list[dict[str, Any]] = []
    for raw in lines:
        line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        line = line.strip()
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk:
            continue
        try:
            events.append(json.loads(chunk))
        except json.JSONDecodeError:
            events.append({"type": "parse_error", "raw": chunk[:200]})
    return events


def check_agent_v2_sse(
    client: httpx.Client,
    base: str,
    *,
    workspace_id: str | None,
    question: str,
    thread_id: str | None,
    timeout: float,
) -> CheckResult:
    """POST ``/v2/agent/query`` with ``Accept: text/event-stream``."""
    url = f"{base.rstrip('/')}/v2/agent/query"
    payload: dict[str, Any] = {"question": question}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if thread_id:
        payload["thread_id"] = thread_id

    events: list[dict[str, Any]] = []
    try:
        stream_timeout = httpx.Timeout(connect=20.0, read=timeout, write=120.0, pool=15.0)
        with client.stream(
            "POST",
            url,
            json=payload,
            headers={"Accept": "text/event-stream", **_extra_headers()},
            timeout=stream_timeout,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                events.extend(_parse_sse_lines([line]))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("agent_v2_sse", False, str(exc), {"partial_event_count": len(events)})

    types = [e.get("type") for e in events if isinstance(e, dict)]
    issues: list[str] = []
    if "intent_classified" not in types:
        issues.append("missing_intent_classified")
    if "final_answer" not in types:
        issues.append("missing_final_answer")
    if any(t == "error" for t in types):
        err_ev = next((e for e in events if e.get("type") == "error"), {})
        issues.append(f"stream_error_event: {err_ev.get('detail', err_ev)!s}"[:300])
    if thread_id:
        if "context_compacted" not in types:
            issues.append("missing_context_compacted_for_thread_id")
        fa = next((e for e in events if e.get("type") == "final_answer"), {})
        if fa.get("thread_id") != thread_id:
            issues.append(f"final_answer_thread_id_mismatch got={fa.get('thread_id')!r}")
        if os.environ.get("AGENT_LIVE_GATE_CH4", "").strip() in ("1", "true", "yes"):
            fa_trace = fa.get("tool_trace") or []
            fa_tools = [x.get("tool") for x in fa_trace if isinstance(x, dict)]
            if "session_init" not in fa_tools:
                issues.append("sse_final_missing_session_init")

    ok = not issues
    return CheckResult(
        "agent_v2_sse",
        ok,
        "; ".join(issues) if issues else "ok",
        {"event_types": types, "event_count": len(events)},
    )


def check_multi_turn_digest(
    client: httpx.Client,
    base: str,
    *,
    workspace_id: str | None,
    timeout: float,
) -> CheckResult:
    """Two sync JSON turns with the same thread_id and client history_digest."""
    tid = f"live_check_{uuid.uuid4().hex[:12]}"
    q1 = os.environ.get("AGENT_LIVE_QUESTION_T1", "Reply with exactly: CHECK_TURN_1")
    url = f"{base.rstrip('/')}/v2/agent/query"
    payload1: dict[str, Any] = {"question": q1, "thread_id": tid}
    if workspace_id:
        payload1["workspace_id"] = workspace_id
    try:
        resp1 = client.post(
            url,
            json=payload1,
            headers={"Accept": "application/json", **_extra_headers()},
            timeout=timeout,
        )
        resp1.raise_for_status()
        data1 = resp1.json()
    except Exception as exc:  # noqa: BLE001
        return CheckResult("multi_turn_digest", False, f"turn1: {exc}")

    a1 = str(data1.get("answer") or "").strip()
    if not a1:
        return CheckResult("multi_turn_digest", False, "turn1_empty_answer")

    digest = [{"user": q1[:500], "assistant": a1[:400]}]
    q2 = os.environ.get(
        "AGENT_LIVE_QUESTION_T2",
        "What was the exact phrase I asked you to reply with in my previous message?",
    )
    r2 = check_agent_v2_sync_json(
        client,
        base,
        workspace_id=workspace_id,
        question=q2,
        thread_id=tid,
        history_digest=digest,
    )
    if not r2.ok:
        return CheckResult(
            "multi_turn_digest",
            False,
            f"turn2_failed: {r2.detail}",
            {"turn1_answer_len": len(a1)},
        )

    if os.environ.get("AGENT_LIVE_GATE_CH4", "").strip() in ("1", "true", "yes"):
        tools = r2.data.get("tools") or []
        if "session_init" not in tools:
            return CheckResult(
                "multi_turn_digest",
                False,
                "turn2_missing_session_init",
                {"thread_id": tid, "turn2_tools": tools},
            )

    return CheckResult(
        "multi_turn_digest",
        True,
        "ok",
        {
            "thread_id": tid,
            "turn2_warnings": r2.data.get("warnings"),
            "turn2_tools": r2.data.get("tools"),
        },
    )


def run_default_suite(
    base: str,
    *,
    workspace_id: str | None,
    timeout: float,
    skip_sse: bool,
    skip_multi_turn: bool,
    on_event: Callable[[CheckResult], None] | None = None,
) -> list[CheckResult]:
    """Run all checks; optional callback after each result (e.g. print)."""
    limits = httpx.Limits(max_keepalive_connections=2, max_connections=5)
    timeout_cfg = httpx.Timeout(connect=20.0, read=timeout, write=120.0, pool=15.0)
    results: list[CheckResult] = []
    with httpx.Client(timeout=timeout_cfg, limits=limits) as client:
        res = check_health(client, base)
        results.append(res)
        if on_event:
            on_event(res)

        res = check_agent_v2_sync_json(
            client,
            base,
            workspace_id=workspace_id,
            question=os.environ.get("AGENT_LIVE_QUESTION", "Say hello in one short sentence."),
        )
        results.append(res)
        if on_event:
            on_event(res)

        if not skip_multi_turn:
            res = check_multi_turn_digest(client, base, workspace_id=workspace_id, timeout=timeout)
            results.append(res)
            if on_event:
                on_event(res)

        if not skip_sse:
            tid = f"live_sse_{uuid.uuid4().hex[:10]}"
            res = check_agent_v2_sse(
                client,
                base,
                workspace_id=workspace_id,
                question=os.environ.get(
                    "AGENT_LIVE_QUESTION_SSE",
                    "One-sentence summary of what an academic GraphRAG system does.",
                ),
                thread_id=tid,
                timeout=timeout,
            )
            results.append(res)
            if on_event:
                on_event(res)

    return results
