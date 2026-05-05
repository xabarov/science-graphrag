"""Wall-clock bounded LangGraph ``invoke`` (sync path).

The underlying graph call may continue in the worker thread after a timeout; callers
receive ``AgentGraphDeadlineExceeded`` and should not assume the remote LLM/tools stopped.
See ``docs/runbooks/agent-chat-v2.md``.
"""

from __future__ import annotations

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from time import perf_counter
from typing import Any, Callable

from langgraph.errors import GraphRecursionError
from opentelemetry import context as otel_context
from opentelemetry import trace as trace_api

from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
    resolve_recursion_limit_from_config,
    telemetry_max_tool_calls_from_state,
)
from science_graphrag.config import Settings
from science_graphrag.observability.spans.decorators import add_span_event

logger = logging.getLogger(__name__)

_GRAPH_INVOKE_AFTER_DEADLINE_HOOK: Callable[[dict[str, Any]], None] | None = None
_GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL = 0
_AGENT_GRAPH_POOL: ThreadPoolExecutor | None = None
_AGENT_GRAPH_POOL_WORKERS: int | None = None
_POOL_LOCK = threading.Lock()
_POOL_SIZE_MISMATCH_WARNED = False


def _default_graph_pool_workers() -> int:
    return min(16, max(4, (os.cpu_count() or 2) * 2))


def _effective_graph_invoke_max_workers(settings: Settings | None) -> int:
    if settings is None:
        return _default_graph_pool_workers()
    raw = int(getattr(settings, "agent_graph_invoke_max_workers", 0) or 0)
    if raw <= 0:
        return _default_graph_pool_workers()
    return max(1, min(32, raw))


def _get_agent_graph_pool(settings: Settings | None) -> ThreadPoolExecutor:
    """Process-local pool; worker count fixed at first use (restart process to apply change)."""

    global _AGENT_GRAPH_POOL, _AGENT_GRAPH_POOL_WORKERS, _POOL_SIZE_MISMATCH_WARNED  # pylint: disable=global-statement
    desired = _effective_graph_invoke_max_workers(settings)
    with _POOL_LOCK:
        if _AGENT_GRAPH_POOL is None:
            _AGENT_GRAPH_POOL = ThreadPoolExecutor(
                max_workers=desired,
                thread_name_prefix="agent_graph",
            )
            _AGENT_GRAPH_POOL_WORKERS = desired
        elif _AGENT_GRAPH_POOL_WORKERS != desired and not _POOL_SIZE_MISMATCH_WARNED:
            _POOL_SIZE_MISMATCH_WARNED = True
            logger.warning(
                "agent_graph_invoke max_workers=%s differs from existing pool (%s); "
                "restart API workers to apply. See docs/runbooks/agent-chat-v2.md.",
                desired,
                _AGENT_GRAPH_POOL_WORKERS,
            )
        return _AGENT_GRAPH_POOL


def reset_agent_graph_executor_for_tests() -> None:
    """Shutdown pool and clear observability hooks (tests only)."""

    global _AGENT_GRAPH_POOL, _AGENT_GRAPH_POOL_WORKERS, _POOL_SIZE_MISMATCH_WARNED  # pylint: disable=global-statement
    global _GRAPH_INVOKE_AFTER_DEADLINE_HOOK, _GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL  # pylint: disable=global-statement
    with _POOL_LOCK:
        if _AGENT_GRAPH_POOL is not None:
            _AGENT_GRAPH_POOL.shutdown(wait=False, cancel_futures=False)
        _AGENT_GRAPH_POOL = None
        _AGENT_GRAPH_POOL_WORKERS = None
        _POOL_SIZE_MISMATCH_WARNED = False
    _GRAPH_INVOKE_AFTER_DEADLINE_HOOK = None
    _GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL = 0


def set_graph_invoke_after_deadline_hook(
    hook: Callable[[dict[str, Any]], None] | None,
) -> None:
    """Register callback for graph completion after response deadline (tests / diagnostics)."""

    global _GRAPH_INVOKE_AFTER_DEADLINE_HOOK  # pylint: disable=global-statement
    _GRAPH_INVOKE_AFTER_DEADLINE_HOOK = hook


def graph_invoke_completed_after_deadline_total() -> int:
    """Count of worker threads that finished invoke after a response deadline (process lifetime)."""

    return int(_GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL)


def _invoke_graph_with_attached_otel_context(
    parent_ctx: object,
    graph: Any,
    state: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    token = otel_context.attach(parent_ctx)
    try:
        try:
            return graph.invoke(state, config=config)
        except GraphRecursionError as exc:
            recursion_limit = resolve_recursion_limit_from_config(config)
            add_span_event(
                "agent.graph_recursion_limit_hit",
                {
                    "recursion_limit": int(recursion_limit),
                    "agent.runtime": str(state.get("metadata", {}).get("agent_runtime") or ""),
                    "agent.max_tool_calls": telemetry_max_tool_calls_from_state(state),
                },
            )
            raise AgentGraphRecursionLimitExceeded(
                recursion_limit=recursion_limit,
                latest_state=None,
                message=None,
            ) from exc
    finally:
        otel_context.detach(token)


def invoke_graph_with_deadline(
    graph: Any,
    state: dict[str, Any],
    *,
    config: dict[str, Any],
    timeout_seconds: float,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run ``graph.invoke`` in a worker thread; raise if wall time exceeds ``timeout_seconds``."""
    if timeout_seconds <= 0:
        try:
            return graph.invoke(state, config=config)
        except GraphRecursionError as exc:
            recursion_limit = resolve_recursion_limit_from_config(config)
            add_span_event(
                "agent.graph_recursion_limit_hit",
                {
                    "recursion_limit": int(recursion_limit),
                    "agent.runtime": str(state.get("metadata", {}).get("agent_runtime") or ""),
                    "agent.max_tool_calls": telemetry_max_tool_calls_from_state(state),
                },
            )
            raise AgentGraphRecursionLimitExceeded(
                recursion_limit=recursion_limit,
                latest_state=None,
                message=None,
            ) from exc

    pool = _get_agent_graph_pool(settings)
    parent_ctx = otel_context.get_current()
    parent_span = trace_api.get_current_span()
    sc = parent_span.get_span_context()
    trace_id_hex = format(sc.trace_id, "032x") if sc.is_valid else ""

    exceeded_at_holder: list[float] = [0.0]

    fut = pool.submit(
        _invoke_graph_with_attached_otel_context,
        parent_ctx,
        graph,
        state,
        config=config,
    )

    def _on_done(f: Any) -> None:
        global _GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL  # pylint: disable=global-statement
        try:
            f.result()
        except Exception:  # noqa: BLE001
            pass
        t_deadline = float(exceeded_at_holder[0])
        lag = max(0.0, perf_counter() - t_deadline) if t_deadline > 0.0 else 0.0
        payload = {
            "lag_seconds": float(lag),
            "timeout_seconds": float(timeout_seconds),
            "trace_id_hex": trace_id_hex,
        }
        _GRAPH_COMPLETED_AFTER_DEADLINE_TOTAL += 1
        try:
            _msg = (
                "agent.graph_invoke_finished_after_response_deadline "
                "lag_seconds=%.3f timeout_seconds=%s trace_id=%s"
            )
            logger.info(
                _msg,
                lag,
                timeout_seconds,
                trace_id_hex or "(none)",
            )
        except Exception:  # noqa: BLE001
            # Closed streams (pytest) or logging misconfiguration must not break worker threads.
            pass
        hook = _GRAPH_INVOKE_AFTER_DEADLINE_HOOK
        if hook is not None:
            hook(payload)
        try:
            if parent_span.is_recording():
                parent_span.add_event(
                    "agent.graph_invoke_finished_after_response_deadline",
                    attributes={
                        "lag_seconds": float(lag),
                        "timeout_seconds": float(timeout_seconds),
                        "trace_id_hex": trace_id_hex,
                    },
                )
        except Exception:  # noqa: BLE001
            pass

    try:
        return fut.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        exceeded_at_holder[0] = perf_counter()
        fut.add_done_callback(_on_done)
        add_span_event(
            "agent.graph_invoke_deadline_exceeded",
            {
                "timeout_seconds": float(timeout_seconds),
                "worker_may_continue": True,
                "deadline_kind": "response_only",
            },
        )
        raise AgentGraphDeadlineExceeded(
            timeout_seconds=timeout_seconds,
            message=f"LangGraph invoke exceeded {timeout_seconds}s",
        ) from exc
