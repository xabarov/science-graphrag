"""Thread-level insight snapshot (Epic A / Train T1 skeleton).

Builds a reproducible ``thread_insight`` artifact from stored turn digests using
uniform chunking and bounded parallel *stub* summarizers (deterministic text).
LLM-backed summaries and prompt injection (A2) are follow-ups.

See: ``docs/specs/agent-chat-v1.md`` §Summarization modes.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.config import Settings


def _chunk_digests_uniform(
    digests: list[dict[str, Any]],
    max_chunks: int,
) -> list[list[dict[str, Any]]]:
    """Split ``digests`` into up to ``max_chunks`` contiguous groups (deterministic)."""
    n = len(digests)
    if n == 0:
        return []
    k = min(max(1, max_chunks), n)
    q, r = divmod(n, k)
    out: list[list[dict[str, Any]]] = []
    idx = 0
    for i in range(k):
        sz = q + (1 if i < r else 0)
        chunk = digests[idx : idx + sz]
        if chunk:
            out.append(chunk)
        idx += sz
    return out


def _deterministic_chunk_summary(chunk: list[dict[str, Any]], chunk_id: str) -> str:
    """Cheap stub summary: structured digest lines (stable for tests / trace audit)."""
    lines: list[str] = [f"chunk={chunk_id}"]
    for j, digest in enumerate(chunk):
        ui = str(digest.get("user_intent") or "")[:160]
        ac = str(digest.get("answer_class") or "")
        tools = digest.get("tools_used") or []
        lines.append(f"  t{j}: class={ac} tools={tools} intent={ui!r}")
    return "\n".join(lines)


def _parallel_chunk_summaries(
    digests: list[dict[str, Any]],
    *,
    max_chunks: int,
    max_workers_cap: int,
) -> tuple[list[str], int, int]:
    """Return (chunk_summaries in order, wall_ms, worker_count)."""
    chunks = _chunk_digests_uniform(digests, max_chunks)
    if not chunks:
        return [], 0, 0
    workers = min(len(chunks), max(1, max_workers_cap))
    summaries: list[str | None] = [None] * len(chunks)
    t0 = time.monotonic()

    def _work(idx: int, ch: list[dict[str, Any]]) -> tuple[int, str]:
        return idx, _deterministic_chunk_summary(ch, f"c{idx}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, i, ch) for i, ch in enumerate(chunks)]
        for fut in as_completed(futures):
            idx, text = fut.result()
            summaries[idx] = text
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    ordered = [s for s in summaries if isinstance(s, str)]
    return ordered, elapsed_ms, workers


def build_thread_insight_snapshot(
    digests: list[dict[str, Any]],
    *,
    settings: Settings,
    prev_version: int,
    turn_counter: int,
) -> dict[str, Any] | None:
    """Assemble ``session_meta.thread_insight`` payload or ``None`` if below threshold."""
    if len(digests) < int(settings.agent_thread_insights_min_digests):
        return None
    summaries, gen_ms, workers = _parallel_chunk_summaries(
        digests,
        max_chunks=int(settings.agent_thread_insights_max_chunks),
        max_workers_cap=int(settings.agent_thread_insights_max_workers),
    )
    if not summaries:
        return None
    current = "## thread_insight (skeleton)\n" + "\n\n".join(summaries)
    n = len(digests)
    chunk_ids = [f"c{i}" for i in range(len(summaries))]
    audit: dict[str, Any] = {
        "schema_version": "thread_insight_audit_v1",
        "chunk_count": len(summaries),
        "worker_count": workers,
        "generation_ms": gen_ms,
        "source_turn_start": 0,
        "source_turn_end": max(0, n - 1),
        "digest_count": n,
        "turn_counter": turn_counter,
        "stale_reason": None,
        "boundary_trigger": "post_turn_digest",
        "mode": "deterministic_stub",
    }
    snapshot: dict[str, Any] = {
        "current": current,
        "version": int(prev_version) + 1,
        "sources": {
            "chunk_ids": chunk_ids,
            "digest_count": n,
            "turn_range": [0, max(0, n - 1)],
        },
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "section_budgets": {
            "max_chunks": int(settings.agent_thread_insights_max_chunks),
            "max_workers": int(settings.agent_thread_insights_max_workers),
        },
        "compaction_boundary": {
            "trigger": "post_turn_digest",
            "note": "TTL / invalidation policy deferred to Epic A2",
        },
        "audit": audit,
    }
    return snapshot


def maybe_refresh_thread_insight_after_turn(thread_id: str, *, settings: Settings) -> None:
    """Persist a new thread insight when enabled and enough digests exist."""
    if not settings.agent_thread_insights_enabled:
        return
    tid = (thread_id or "").strip()
    if not tid:
        return
    backend = get_session_memory_backend()
    ent = backend.get_session_copy(tid)
    digests = [d for d in (ent.get("digests") or []) if isinstance(d, dict)]
    meta = ent.get("session_meta") or {}
    meta_dict = dict(meta) if isinstance(meta, dict) else {}
    turn_counter = int(meta_dict.get("turn_counter") or 0)
    prev = meta_dict.get("thread_insight")
    prev_ver = 0
    if isinstance(prev, dict):
        try:
            prev_ver = int(prev.get("version") or 0)
        except (TypeError, ValueError):
            prev_ver = 0
    snap = build_thread_insight_snapshot(
        digests,
        settings=settings,
        prev_version=prev_ver,
        turn_counter=turn_counter,
    )
    if snap is None:
        return
    backend.apply_thread_insight_snapshot(tid, snapshot=snap)
