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

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded

_MAX_WORKERS = min(16, max(4, (os.cpu_count() or 2) * 2))
_AGENT_GRAPH_POOL = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="agent_graph")


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

    fut = _AGENT_GRAPH_POOL.submit(graph.invoke, state, config=config)
    try:
        return fut.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        raise AgentGraphDeadlineExceeded(
            timeout_seconds=timeout_seconds,
            message=f"LangGraph invoke exceeded {timeout_seconds}s",
        ) from exc
