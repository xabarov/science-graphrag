"""HTTP helpers for compaction turn review (agent query + wait heartbeats)."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Any

import httpx


def build_auth_headers() -> dict[str, str]:
    """Build request headers from ``AGENT_LIVE_*`` env (auth / admin)."""
    out: dict[str, str] = {"Accept": "application/json"}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


def stderr_wait_heartbeat_line(*, turn_idx: int, thread_id: str, elapsed_ms: int) -> str:
    """Machine-readable stderr line while blocking on ``/v2/agent/query`` (W3 contract)."""
    return json.dumps(
        {
            "kind": "compaction_turn_wait_heartbeat",
            "lane": "compaction_turn_review",
            "turn": turn_idx,
            "thread_id": thread_id,
            "elapsed_ms": elapsed_ms,
        },
        ensure_ascii=False,
    )


def single_turn(
    client: httpx.Client,
    *,
    base_url: str,
    question: str,
    thread_id: str,
    workspace_id: str | None,
) -> dict[str, Any]:
    """POST ``/v2/agent/query`` and return a flattened per-turn summary dict."""
    payload: dict[str, Any] = {"question": question, "thread_id": thread_id}
    if workspace_id:
        payload["workspace_id"] = workspace_id
    res = client.post(f"{base_url}/v2/agent/query", json=payload, headers=build_auth_headers())
    res.raise_for_status()
    body = res.json()
    rm = body.get("run_metadata") if isinstance(body, dict) else {}
    comp = rm.get("compaction") if isinstance(rm, dict) else {}
    comp_audit = rm.get("compaction_audit") if isinstance(rm, dict) else {}
    llm_compact = comp_audit.get("llm_compact") if isinstance(comp_audit, dict) else {}
    side_ratio = (
        llm_compact.get("side_llm_cache_read_ratio") if isinstance(llm_compact, dict) else None
    )
    l4_skip_reason = (
        str(comp_audit.get("l4_skip_reason") or "").strip() if isinstance(comp_audit, dict) else ""
    ) or None
    paper_restored = (
        int(rm.get("post_compact_paper_sources_restored_count") or 0) if isinstance(rm, dict) else 0
    )
    return {
        "thread_id": body.get("thread_id"),
        "answer_class": body.get("answer_class"),
        "duration_ms": body.get("duration_ms"),
        "warnings": body.get("warnings"),
        "tool_trace_len": len(body.get("tool_trace") or []),
        "compaction": comp if isinstance(comp, dict) else {},
        "l4_skip_reason": l4_skip_reason,
        "side_llm_cache_read_ratio": side_ratio,
        "post_compact_paper_sources_restored_count": paper_restored,
    }


def single_turn_with_wait_heartbeat(
    client: httpx.Client,
    *,
    base_url: str,
    question: str,
    thread_id: str,
    workspace_id: str | None,
    turn_idx: int,
    hb_sec: float,
) -> dict[str, Any]:
    """Run ``single_turn`` while emitting stderr heartbeats during blocking HTTP wait."""
    done = threading.Event()
    t0 = time.perf_counter()

    def _hb_loop() -> None:
        while not done.wait(timeout=max(5.0, float(hb_sec))):
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            print(
                stderr_wait_heartbeat_line(
                    turn_idx=turn_idx, thread_id=thread_id, elapsed_ms=elapsed_ms
                ),
                file=sys.stderr,
                flush=True,
            )

    hb_thread = threading.Thread(target=_hb_loop, name="compaction-review-hb", daemon=True)
    hb_thread.start()
    try:
        return single_turn(
            client,
            base_url=base_url,
            question=question,
            thread_id=thread_id,
            workspace_id=workspace_id,
        )
    finally:
        done.set()


__all__ = [
    "build_auth_headers",
    "single_turn",
    "single_turn_with_wait_heartbeat",
    "stderr_wait_heartbeat_line",
]
