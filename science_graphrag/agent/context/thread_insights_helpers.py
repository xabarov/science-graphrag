"""Pure helpers for thread digest chunking, freshness, and parallel summaries."""

from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from typing import Any, Literal

from science_graphrag.config import Settings

# Per-chunk worker ceiling (stub work is fast; avoids hung threads if workers block).
_CHUNK_FUTURE_TIMEOUT_S = 45.0

RefreshDecision = Literal[
    "refresh",
    "skip_fresh",
    "skip_below_threshold",
    "skip_circuit_open",
    "skip_lock_held",
    "skip_build_failed",
]
StaleReason = Literal["turn_delta", "ttl", "high_churn", "manual"]


def approx_tokens(text: str) -> int:
    return max(0, len(text) // 4)


def parse_generated_at(ts: str | None) -> datetime | None:
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def digest_blob_for_estimate(digests: list[dict[str, Any]]) -> str:
    try:
        return json.dumps(digests, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def tool_event_churn(digests: list[dict[str, Any]], window: int) -> int:
    n = max(0, len(digests))
    if n == 0:
        return 0
    w = min(max(1, window), n)
    tail = digests[-w:]
    count = 0
    for d in tail:
        tools = d.get("tools_used") or []
        if isinstance(tools, list):
            count += len([x for x in tools if str(x).strip()])
        else:
            count += 1
    return count


def preserved_segment(digests: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for d in digests[-3:]:
        ui = str(d.get("user_intent") or "")[:80].strip()
        if ui:
            parts.append(ui)
    seg = " | ".join(parts)
    return seg[:400] if seg else "(empty window)"


def chunk_digests_uniform(
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


def deterministic_chunk_summary(chunk: list[dict[str, Any]], chunk_id: str) -> str:
    """Cheap stub summary: structured digest lines (stable for tests / trace audit)."""
    lines: list[str] = [f"chunk={chunk_id}"]
    for j, digest in enumerate(chunk):
        ui = str(digest.get("user_intent") or "")[:160]
        ac = str(digest.get("answer_class") or "")
        tools = digest.get("tools_used") or []
        lines.append(f"  t{j}: class={ac} tools={tools} intent={ui!r}")
    return "\n".join(lines)


def collect_chunk_summaries(
    futures: list[Future[tuple[int, str]]],
    summaries: list[str | None],
    *,
    timeout: float,
) -> None:
    """Fill ``summaries`` slots from executor futures; cancel on timeout."""
    pending = set(futures)
    while pending:
        done, pending = wait(pending, timeout=timeout, return_when=FIRST_COMPLETED)
        if not done:
            for fut in pending:
                fut.cancel()
            raise TimeoutError("thread_insights chunk worker timed out")
        for fut in done:
            idx, text = fut.result(timeout=timeout)
            summaries[idx] = text


def parallel_chunk_summaries(
    digests: list[dict[str, Any]],
    *,
    max_chunks: int,
    max_workers_cap: int,
    result_timeout_s: float = _CHUNK_FUTURE_TIMEOUT_S,
) -> tuple[list[str], int, int]:
    """Return (chunk_summaries in order, wall_ms, worker_count)."""
    chunks = chunk_digests_uniform(digests, max_chunks)
    if not chunks:
        return [], 0, 0
    workers = min(len(chunks), max(1, max_workers_cap))
    summaries: list[str | None] = [None] * len(chunks)
    t0 = time.monotonic()
    timeout = max(5.0, min(120.0, float(result_timeout_s)))

    def _work(idx: int, ch: list[dict[str, Any]]) -> tuple[int, str]:
        return idx, deterministic_chunk_summary(ch, f"c{idx}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, i, ch) for i, ch in enumerate(chunks)]
        collect_chunk_summaries(futures, summaries, timeout=timeout)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    ordered = [s for s in summaries if isinstance(s, str)]
    return ordered, elapsed_ms, workers


def built_turn_from_prev_insight(prev_insight: dict[str, Any]) -> int | None:
    """Turn index when the previous snapshot was built (supports legacy audit shapes)."""
    prev_audit = prev_insight.get("audit")
    if not isinstance(prev_audit, dict):
        return None
    raw_built = prev_audit.get("built_at_turn_counter")
    if raw_built is None or raw_built == "":
        raw_built = prev_audit.get("turn_counter")
    try:
        built = int(raw_built or 0)
    except (TypeError, ValueError):
        return None
    return built if built > 0 else None


def boundary_trigger_for_stale(stale: StaleReason | None) -> str:
    if stale == "high_churn":
        return "high_churn_refresh"
    if stale == "ttl":
        return "ttl_stale"
    if stale == "manual":
        return "manual_refresh"
    if stale == "turn_delta":
        return "turn_delta_stale"
    return "post_turn_digest"


def freshness_flags(
    *,
    digests: list[dict[str, Any]],
    turn_counter: int,
    built_turn: int,
    prev_insight: dict[str, Any],
    settings: Settings,
) -> tuple[bool, bool, bool]:
    """Return (turn_delta_hit, ttl_hit, churn_hit) for an existing snapshot."""
    delta_needed = max(1, int(settings.agent_thread_insights_stale_after_turn_delta))
    turns_since = turn_counter - built_turn

    gen_at = parse_generated_at(str(prev_insight.get("generated_at") or ""))
    ttl_sec = int(settings.agent_thread_insights_ttl_seconds)
    ttl_hit = False
    if ttl_sec > 0 and gen_at is not None:
        age = (datetime.now(UTC) - gen_at).total_seconds()
        ttl_hit = age >= float(ttl_sec)

    win = max(1, int(settings.agent_thread_insights_high_churn_window_digests))
    churn = tool_event_churn(digests, win)
    churn_hit = churn >= int(settings.agent_thread_insights_high_churn_min_tool_events)

    turn_delta_hit = turns_since >= delta_needed
    return turn_delta_hit, ttl_hit, churn_hit


# Private aliases matching historical thread_insights.py names
_approx_tokens = approx_tokens
_parse_generated_at = parse_generated_at
_digest_blob_for_estimate = digest_blob_for_estimate
_tool_event_churn = tool_event_churn
_preserved_segment = preserved_segment
_chunk_digests_uniform = chunk_digests_uniform
_deterministic_chunk_summary = deterministic_chunk_summary
_parallel_chunk_summaries = parallel_chunk_summaries
_built_turn_from_prev_insight = built_turn_from_prev_insight
_collect_chunk_summaries = collect_chunk_summaries
_boundary_trigger_for_stale = boundary_trigger_for_stale
_freshness_flags = freshness_flags
CHUNK_FUTURE_TIMEOUT_S = _CHUNK_FUTURE_TIMEOUT_S
