"""Thread-level insight snapshot (Epic A1).

Deterministic chunking + bounded parallel stub summarizers; freshness, circuit-breaker,
explicit compaction boundary artifact, and control-plane telemetry. LLM synthesis and
prompt injection remain follow-ups (see ``docs/specs/agent-chat-v1.md``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from datetime import UTC, datetime
from typing import Any, Literal

from science_graphrag.agent.context.session_backend import (
    SessionMemoryBackend,
    get_session_memory_backend,
)
from science_graphrag.agent.forked_runtime import (
    side_llm_fork_metadata,
    synthesize_thread_insight_markdown,
)
from science_graphrag.config import Settings

logger = logging.getLogger(__name__)

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


def _approx_tokens(text: str) -> int:
    return max(0, len(text) // 4)


def _parse_generated_at(ts: str | None) -> datetime | None:
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


def _digest_blob_for_estimate(digests: list[dict[str, Any]]) -> str:
    try:
        return json.dumps(digests, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def _tool_event_churn(digests: list[dict[str, Any]], window: int) -> int:
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


def _preserved_segment(digests: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for d in digests[-3:]:
        ui = str(d.get("user_intent") or "")[:80].strip()
        if ui:
            parts.append(ui)
    seg = " | ".join(parts)
    return seg[:400] if seg else "(empty window)"


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
    result_timeout_s: float = _CHUNK_FUTURE_TIMEOUT_S,
) -> tuple[list[str], int, int]:
    """Return (chunk_summaries in order, wall_ms, worker_count)."""
    chunks = _chunk_digests_uniform(digests, max_chunks)
    if not chunks:
        return [], 0, 0
    workers = min(len(chunks), max(1, max_workers_cap))
    summaries: list[str | None] = [None] * len(chunks)
    t0 = time.monotonic()
    timeout = max(5.0, min(120.0, float(result_timeout_s)))

    def _work(idx: int, ch: list[dict[str, Any]]) -> tuple[int, str]:
        return idx, _deterministic_chunk_summary(ch, f"c{idx}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_work, i, ch) for i, ch in enumerate(chunks)]
        _collect_chunk_summaries(futures, summaries, timeout=timeout)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    ordered = [s for s in summaries if isinstance(s, str)]
    return ordered, elapsed_ms, workers


def _built_turn_from_prev_insight(prev_insight: dict[str, Any]) -> int | None:
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


def _collect_chunk_summaries(
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


def _boundary_trigger_for_stale(stale: StaleReason | None) -> str:
    if stale == "high_churn":
        return "high_churn_refresh"
    if stale == "ttl":
        return "ttl_stale"
    if stale == "manual":
        return "manual_refresh"
    if stale == "turn_delta":
        return "turn_delta_stale"
    return "post_turn_digest"


def _freshness_flags(
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

    gen_at = _parse_generated_at(str(prev_insight.get("generated_at") or ""))
    ttl_sec = int(settings.agent_thread_insights_ttl_seconds)
    ttl_hit = False
    if ttl_sec > 0 and gen_at is not None:
        age = (datetime.now(UTC) - gen_at).total_seconds()
        ttl_hit = age >= float(ttl_sec)

    win = max(1, int(settings.agent_thread_insights_high_churn_window_digests))
    churn = _tool_event_churn(digests, win)
    churn_hit = churn >= int(settings.agent_thread_insights_high_churn_min_tool_events)

    turn_delta_hit = turns_since >= delta_needed
    return turn_delta_hit, ttl_hit, churn_hit


def _decide_refresh(  # pylint: disable=too-many-return-statements
    *,
    digests: list[dict[str, Any]],
    turn_counter: int,
    prev_insight: dict[str, Any] | None,
    meta: dict[str, Any],
    settings: Settings,
) -> tuple[RefreshDecision, StaleReason | None]:
    """Explicit refresh/skip branches (policy table)."""
    min_d = int(settings.agent_thread_insights_min_digests)
    if len(digests) < min_d:
        return "skip_below_threshold", None

    circuit = meta.get("insight_circuit") if isinstance(meta.get("insight_circuit"), dict) else {}
    open_until = int(circuit.get("open_until_turn") or 0)
    if open_until and turn_counter < open_until:
        return "skip_circuit_open", None

    if settings.agent_thread_insights_force_manual_stale:
        return "refresh", "manual"

    if not isinstance(prev_insight, dict):
        return "refresh", None

    built_turn = _built_turn_from_prev_insight(prev_insight)
    if not built_turn:
        return "refresh", "turn_delta"

    td, ttl_hit, churn_hit = _freshness_flags(
        digests=digests,
        turn_counter=turn_counter,
        built_turn=built_turn,
        prev_insight=prev_insight,
        settings=settings,
    )
    if not td and not ttl_hit and not churn_hit:
        return "skip_fresh", None
    if churn_hit:
        return "refresh", "high_churn"
    if ttl_hit:
        return "refresh", "ttl"
    return "refresh", "turn_delta"


def _record_insight_control(
    backend: SessionMemoryBackend,
    thread_id: str,
    *,
    turn_counter: int,
    decision: RefreshDecision,
    stale_reason: StaleReason | None,
    extra: dict[str, Any] | None = None,
) -> None:
    ctrl: dict[str, Any] = {
        "schema_version": "thread_insight_control_v1",
        "last_turn": int(turn_counter),
        "refresh_decision": decision,
        "last_stale_reason": stale_reason,
    }
    if extra:
        ctrl.update(extra)
    backend.patch_session_meta(thread_id, patch={"thread_insight_control": ctrl})


def _circuit_record_failure(
    backend: SessionMemoryBackend,
    thread_id: str,
    *,
    turn_counter: int,
    settings: Settings,
) -> None:
    ent = backend.get_session_copy(thread_id)
    meta = dict(ent.get("session_meta") or {})
    c = (
        dict(meta.get("insight_circuit") or {})
        if isinstance(meta.get("insight_circuit"), dict)
        else {}
    )
    failures = int(c.get("consecutive_failures") or 0) + 1
    max_f = max(1, int(settings.agent_thread_insights_max_consecutive_failures))
    skip_n = max(1, int(settings.agent_thread_insights_circuit_open_skip_turns))
    open_until = int(c.get("open_until_turn") or 0)
    if failures >= max_f:
        open_until = max(open_until, int(turn_counter) + skip_n)
    patch = {
        "insight_circuit": {
            "consecutive_failures": failures,
            "open_until_turn": open_until,
            "last_failure_turn": int(turn_counter),
        }
    }
    backend.patch_session_meta(thread_id, patch=patch)


def _merge_success_control_patch(
    *,
    turn_counter: int,
    stale: StaleReason | None,
    snap: dict[str, Any],
) -> dict[str, Any]:
    """Single session_meta patch after successful snapshot (circuit reset + control plane)."""
    aud = snap.get("audit") if isinstance(snap.get("audit"), dict) else {}
    ctrl: dict[str, Any] = {
        "schema_version": "thread_insight_control_v1",
        "last_turn": int(turn_counter),
        "refresh_decision": "refresh",
        "last_stale_reason": stale,
        "version": snap.get("version"),
        "chunk_count": aud.get("chunk_count"),
    }
    return {
        "insight_circuit": {"consecutive_failures": 0, "open_until_turn": 0},
        "thread_insight_control": ctrl,
    }


def _fingerprint_digest_window(digs: list[dict[str, Any]]) -> str:
    """Stable fingerprint for the digest window (append-only incremental detection)."""
    slim: list[dict[str, Any]] = []
    for d in digs:
        if not isinstance(d, dict):
            continue
        tools = d.get("tools_used") or []
        tlist = [str(x) for x in tools if str(x).strip()][:16] if isinstance(tools, list) else []
        slim.append(
            {
                "user_intent": str(d.get("user_intent") or "")[:240],
                "answer_excerpt": str(d.get("answer_excerpt") or "")[:360],
                "answer_class": str(d.get("answer_class") or ""),
                "tools_used": tlist,
            }
        )
    raw = json.dumps(slim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def _norm_conflict_text(text: str) -> str:
    return "".join(ch.lower() for ch in str(text or "") if ch.isalnum())


def _collect_synthesis_conflicts(
    prev_insight_body: str,
    new_digest: dict[str, Any],
) -> list[dict[str, Any]]:
    """Detect coarse contradictions between prior insight text and the newest digest."""
    out: list[dict[str, Any]] = []
    ae = str(new_digest.get("answer_excerpt") or "")
    if "__INSIGHT_CONFLICT__" in ae:
        out.append({"kind": "explicit_marker", "field": "answer_excerpt"})
    pb = _norm_conflict_text(prev_insight_body)
    an = _norm_conflict_text(ae)
    if not an:
        return out
    # Short tokens like true/false match inside unrelated alnum-stripped text; keep longer pairs.
    polarity_pairs = (
        ("increased", "decreased"),
        ("increase", "decrease"),
        ("positive", "negative"),
    )
    seen: set[tuple[str, str]] = set()
    for a, b in polarity_pairs:
        if a in pb and b in an:
            key = (a, b)
            if key not in seen:
                seen.add(key)
                out.append({"kind": "polarity_mismatch", "pair": [a, b]})
        elif b in pb and a in an:
            key = (b, a)
            if key not in seen:
                seen.add(key)
                out.append({"kind": "polarity_mismatch", "pair": [b, a]})
    return out


def _append_synthesis_cross_conflicts(
    snap: dict[str, Any],
    prev_insight: dict[str, Any] | None,
    tail_digest: dict[str, Any],
) -> None:
    """Merge cross-turn conflicts into ``snap['audit']`` (non-incremental builds)."""
    if not isinstance(snap, dict) or not isinstance(tail_digest, dict):
        return
    if not isinstance(prev_insight, dict):
        return
    prev_body = str(prev_insight.get("current") or "").strip()
    if not prev_body:
        return
    found = _collect_synthesis_conflicts(prev_body, tail_digest)
    if not found:
        return
    aud = dict(snap.get("audit") or {})
    merged = [dict(x) for x in aud.get("synthesis_conflicts") or [] if isinstance(x, dict)]
    merged.extend(found)
    aud["synthesis_conflicts"] = merged
    aud["synthesis_conflict"] = True
    snap["audit"] = aud


def _maybe_llm_synthesize_thread_insight_incremental(
    prev_body: str,
    delta_summary: str,
    delta_blob: str,
    *,
    settings: Settings,
) -> tuple[str, str, dict[str, Any], int | None, str | None]:
    """Incremental variant: merge prior markdown with one new deterministic chunk summary."""
    llm_on = bool(getattr(settings, "agent_thread_insights_llm_synthesis_enabled", False))
    api_ok = bool(str(getattr(settings, "extraction_llm_api_key", None) or "").strip())
    stub = (
        str(prev_body).rstrip()
        + "\n\n## incremental_delta\n\n"
        + str(delta_summary).strip()
    )
    if not (llm_on and api_ok):
        return (
            stub,
            "deterministic_stub_incremental",
            side_llm_fork_metadata(forked=False),
            None,
            None,
        )
    combined = (
        "Prior thread insight (markdown; factual anchor):\n"
        f"{str(prev_body).strip()[:6000]}\n\n"
        "New tail digest chunk summary (deterministic):\n"
        f"{str(delta_summary).strip()}"
    )
    return _maybe_llm_synthesize_thread_insight(
        [combined],
        delta_blob,
        settings=settings,
    )


def try_build_thread_insight_snapshot_incremental(  # pylint: disable=too-many-locals,too-many-return-statements
    digests: list[dict[str, Any]],
    *,
    settings: Settings,
    prev_insight: dict[str, Any],
    prev_version: int,
    turn_counter: int,
    stale_reason: StaleReason | None,
) -> dict[str, Any] | None:
    """Append-only refresh: reuse prior insight body when digest window only grew by the tail."""
    if not bool(getattr(settings, "agent_thread_insights_incremental_enabled", True)):
        return None
    if len(digests) < int(settings.agent_thread_insights_min_digests):
        return None
    prev_aud = prev_insight.get("audit") if isinstance(prev_insight.get("audit"), dict) else {}
    prev_fp = str(prev_aud.get("digest_window_fingerprint") or "")
    if not prev_fp or len(digests) < 2:
        return None
    prefix = digests[:-1]
    if _fingerprint_digest_window(prefix) != prev_fp:
        return None
    prev_body = str(prev_insight.get("current") or "").strip()
    if not prev_body:
        return None
    new_digest = digests[-1]
    ext_to = float(getattr(settings, "extraction_llm_timeout_seconds", 60) or 60)
    summaries, gen_ms, workers = _parallel_chunk_summaries(
        [new_digest],
        max_chunks=1,
        max_workers_cap=1,
        result_timeout_s=max(10.0, min(120.0, ext_to)),
    )
    if not summaries:
        return None
    delta_blob = _digest_blob_for_estimate([new_digest])
    current, mode, fork_meta, side_llm_latency_ms, llm_synthesis_error = (
        _maybe_llm_synthesize_thread_insight_incremental(
            prev_body,
            summaries[0],
            delta_blob,
            settings=settings,
        )
    )
    n = len(digests)
    conflicts = _collect_synthesis_conflicts(prev_body, new_digest)
    pre_tokens = _approx_tokens(_digest_blob_for_estimate(digests)) + 32
    boundary_trigger = _boundary_trigger_for_stale(stale_reason)
    prev_chunks = int(prev_aud.get("chunk_count") or 1)
    audit: dict[str, Any] = {
        "schema_version": "thread_insight_audit_v1",
        "chunk_count": prev_chunks + 1,
        "worker_count": workers,
        "generation_ms": gen_ms,
        "source_turn_start": 0,
        "source_turn_end": max(0, n - 1),
        "digest_count": n,
        "turn_counter": turn_counter,
        "built_at_turn_counter": int(turn_counter),
        "stale_reason": stale_reason,
        "boundary_trigger": boundary_trigger,
        "mode": mode,
        "refresh_mode": "incremental",
        "digest_window_fingerprint": _fingerprint_digest_window(digests),
        "synthesis_conflicts": conflicts,
        "synthesis_conflict": bool(conflicts),
        **fork_meta,
    }
    if side_llm_latency_ms is not None:
        audit["side_llm_latency_ms"] = side_llm_latency_ms
    if llm_synthesis_error:
        audit["llm_synthesis_error"] = llm_synthesis_error
    prev_src = (
        prev_insight.get("sources") if isinstance(prev_insight.get("sources"), dict) else {}
    )
    prev_chunk_ids = [str(x) for x in (prev_src.get("chunk_ids") or []) if str(x).strip()]
    tail_id = f"incr_{int(turn_counter)}"
    incremental_chunk_ids = [*prev_chunk_ids, tail_id] if prev_chunk_ids else [tail_id]
    snapshot: dict[str, Any] = {
        "current": current,
        "version": int(prev_version) + 1,
        "sources": {
            "chunk_ids": incremental_chunk_ids,
            "digest_count": n,
            "turn_range": [0, max(0, n - 1)],
        },
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "section_budgets": {
            "max_chunks": int(settings.agent_thread_insights_max_chunks),
            "max_workers": int(settings.agent_thread_insights_max_workers),
        },
        "compaction_boundary": {
            "schema_version": "thread_insight_compaction_boundary_v1",
            "trigger": boundary_trigger,
            "pre_tokens": int(pre_tokens),
            "source_range": {
                "digest_index_start": 0,
                "digest_index_end": max(0, n - 1),
                "turn_counter": int(turn_counter),
            },
            "preserved_segment": _preserved_segment(digests),
        },
        "audit": audit,
    }
    return snapshot


def _maybe_llm_synthesize_thread_insight(
    summaries: list[str],
    digest_blob: str,
    *,
    settings: Settings,
) -> tuple[str, str, dict[str, Any], int | None, str | None]:
    """Return (markdown_body, mode, fork_meta, side_llm_latency_ms, llm_error_or_none)."""
    current = "## thread_insight (skeleton)\n" + "\n\n".join(summaries)
    mode = "deterministic_stub"
    fork_meta = side_llm_fork_metadata(forked=False)
    side_ms: int | None = None
    err: str | None = None
    llm_on = bool(getattr(settings, "agent_thread_insights_llm_synthesis_enabled", False))
    api_ok = bool(str(getattr(settings, "extraction_llm_api_key", None) or "").strip())
    if not (llm_on and api_ok):
        return current, mode, fork_meta, side_ms, err
    try:
        run = synthesize_thread_insight_markdown(
            settings=settings,
            chunk_summaries=summaries,
            digest_prefix_text=digest_blob,
        )
        side_ms = int(run.latency_ms)
        fork_meta_from_run = side_llm_fork_metadata(
            forked=bool(run.forked),
            side_llm_cache_read_tokens=run.side_llm_cache_read_tokens,
            side_llm_cache_creation_tokens=run.side_llm_cache_creation_tokens,
            side_llm_cache_read_ratio=run.side_llm_cache_read_ratio,
        )
        if run.text.strip():
            body = run.text.strip()
            if not body.lstrip().startswith("#"):
                body = "## thread_insight\n\n" + body
            return (
                body,
                "llm_forked_synthesis",
                fork_meta_from_run,
                side_ms,
                None,
            )
        return (
            current,
            "llm_forked_empty_body_fallback",
            fork_meta_from_run,
            side_ms,
            None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("thread_insight LLM synthesis failed: %s", exc, exc_info=True)
        err = str(exc)[:500]
    return current, mode, fork_meta, side_ms, err


def build_thread_insight_snapshot(  # pylint: disable=too-many-locals
    digests: list[dict[str, Any]],
    *,
    settings: Settings,
    prev_version: int,
    turn_counter: int,
    stale_reason: StaleReason | None,
) -> dict[str, Any] | None:
    """Assemble ``session_meta.thread_insight`` payload or ``None`` if below threshold."""
    if len(digests) < int(settings.agent_thread_insights_min_digests):
        return None
    ext_to = float(getattr(settings, "extraction_llm_timeout_seconds", 60) or 60)
    summaries, gen_ms, workers = _parallel_chunk_summaries(
        digests,
        max_chunks=int(settings.agent_thread_insights_max_chunks),
        max_workers_cap=int(settings.agent_thread_insights_max_workers),
        result_timeout_s=max(10.0, min(120.0, ext_to)),
    )
    if not summaries:
        return None
    digest_blob = _digest_blob_for_estimate(digests)
    current, mode, fork_meta, side_llm_latency_ms, llm_synthesis_error = (
        _maybe_llm_synthesize_thread_insight(summaries, digest_blob, settings=settings)
    )
    n = len(digests)
    chunk_ids = [f"c{i}" for i in range(len(summaries))]
    pre_tokens = _approx_tokens(digest_blob) + 32 * len(summaries)
    boundary_trigger = _boundary_trigger_for_stale(stale_reason)
    audit: dict[str, Any] = {
        "schema_version": "thread_insight_audit_v1",
        "chunk_count": len(summaries),
        "worker_count": workers,
        "generation_ms": gen_ms,
        "source_turn_start": 0,
        "source_turn_end": max(0, n - 1),
        "digest_count": n,
        "turn_counter": turn_counter,
        "built_at_turn_counter": int(turn_counter),
        "stale_reason": stale_reason,
        "boundary_trigger": boundary_trigger,
        "mode": mode,
        **fork_meta,
    }
    if side_llm_latency_ms is not None:
        audit["side_llm_latency_ms"] = side_llm_latency_ms
    if llm_synthesis_error:
        audit["llm_synthesis_error"] = llm_synthesis_error
    audit["digest_window_fingerprint"] = _fingerprint_digest_window(digests)
    audit["refresh_mode"] = "full"
    audit["synthesis_conflicts"] = []
    audit["synthesis_conflict"] = False
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
            "schema_version": "thread_insight_compaction_boundary_v1",
            "trigger": boundary_trigger,
            "pre_tokens": int(pre_tokens),
            "source_range": {
                "digest_index_start": 0,
                "digest_index_end": max(0, n - 1),
                "turn_counter": int(turn_counter),
            },
            "preserved_segment": _preserved_segment(digests),
        },
        "audit": audit,
    }
    return snapshot


def maybe_refresh_thread_insight_after_turn(thread_id: str, *, settings: Settings) -> None:
    """Persist a new thread insight when enabled, fresh, lock-free, and circuit closed."""
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
    prev_dict = dict(prev) if isinstance(prev, dict) else None

    decision, stale = _decide_refresh(
        digests=digests,
        turn_counter=turn_counter,
        prev_insight=prev_dict,
        meta=meta_dict,
        settings=settings,
    )

    if decision != "refresh":
        _record_insight_control(
            backend,
            tid,
            turn_counter=turn_counter,
            decision=decision,
            stale_reason=stale,
        )
        return

    if not backend.compaction_lock_acquire(tid, owner="thread_insight", turn=turn_counter):
        _record_insight_control(
            backend,
            tid,
            turn_counter=turn_counter,
            decision="skip_lock_held",
            stale_reason=stale,
        )
        return

    try:
        prev_ver = 0
        if isinstance(prev_dict, dict):
            try:
                prev_ver = int(prev_dict.get("version") or 0)
            except (TypeError, ValueError):
                prev_ver = 0
        snap = None
        if isinstance(prev_dict, dict):
            snap = try_build_thread_insight_snapshot_incremental(
                digests,
                settings=settings,
                prev_insight=prev_dict,
                prev_version=prev_ver,
                turn_counter=turn_counter,
                stale_reason=stale,
            )
        if snap is None:
            snap = build_thread_insight_snapshot(
                digests,
                settings=settings,
                prev_version=prev_ver,
                turn_counter=turn_counter,
                stale_reason=stale,
            )
        if snap is not None and not (
            isinstance(snap.get("audit"), dict)
            and str((snap.get("audit") or {}).get("refresh_mode") or "") == "incremental"
        ):
            _append_synthesis_cross_conflicts(snap, prev_dict, digests[-1])
        if snap is None:
            _record_insight_control(
                backend,
                tid,
                turn_counter=turn_counter,
                decision="skip_below_threshold",
                stale_reason=stale,
            )
            return
        backend.apply_thread_insight_snapshot(tid, snapshot=snap)
        backend.patch_session_meta(
            tid,
            patch=_merge_success_control_patch(turn_counter=turn_counter, stale=stale, snap=snap),
        )
    except Exception:  # noqa: BLE001
        logger.warning("thread_insight refresh failed for thread_id=%s", tid, exc_info=True)
        _circuit_record_failure(backend, tid, turn_counter=turn_counter, settings=settings)
        _record_insight_control(
            backend,
            tid,
            turn_counter=turn_counter,
            decision="skip_build_failed",
            stale_reason=stale,
            extra={"error": "thread_insight_build_failed"},
        )
    finally:
        backend.compaction_lock_release(tid, owner="thread_insight")
