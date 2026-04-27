"""Wall-clock bounded LangGraph ``invoke`` (sync path).

The underlying graph call may continue in the worker thread after a timeout; callers
receive ``AgentGraphDeadlineExceeded`` and should not assume the remote LLM/tools stopped.
See ``docs/runbooks/agent-chat-v2.md``.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from opentelemetry import context as otel_context

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.observability.spans.decorators import add_span_event

_MAX_WORKERS = min(16, max(4, (os.cpu_count() or 2) * 2))
_AGENT_GRAPH_POOL = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="agent_graph")


def _invoke_graph_with_attached_otel_context(
    parent_ctx: object,
    graph: Any,
    state: dict[str, Any],
    *,
    config: dict[str, Any],
) -> dict[str, Any]:
    token = otel_context.attach(parent_ctx)
    try:
        return graph.invoke(state, config=config)
    finally:
        otel_context.detach(token)


def invoke_graph_with_deadline(
    graph: Any,
    state: dict[str, Any],
    *,
    config: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Run ``graph.invoke`` in a worker thread; raise if wall time exceeds ``timeout_seconds``."""
    if timeout_seconds <= 0:
        return graph.invoke(state, config=config)

    # LangGraph invoke runs in a worker thread here; explicitly attach the
    # current OpenTelemetry context so nested LLM/TOOL/CHAIN spans remain in
    # the same trace tree as ``agent.query``.
    parent_ctx = otel_context.get_current()
    fut = _AGENT_GRAPH_POOL.submit(
        _invoke_graph_with_attached_otel_context,
        parent_ctx,
        graph,
        state,
        config=config,
    )
    try:
        return fut.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
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
