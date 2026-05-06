"""Request-scoped context for agent graph execution (tool surfaces).

LangChain tools do not receive LangGraph state; we set ``thread_id`` around
``invoke`` / ``astream`` so session-backed tools can persist safely.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_agent_graph_thread_id: ContextVar[str | None] = ContextVar("agent_graph_thread_id", default=None)


def get_agent_graph_thread_id() -> str | None:
    """Return active thread id for the current graph invocation, if any."""
    tid = _agent_graph_thread_id.get()
    if isinstance(tid, str) and tid.strip():
        return tid.strip()
    return None


@contextmanager
def agent_graph_thread_id_scope(thread_id: str | None) -> Iterator[None]:
    """Bind ``thread_id`` for the duration of a graph run."""
    token = _agent_graph_thread_id.set((thread_id or "").strip() or None)
    try:
        yield
    finally:
        _agent_graph_thread_id.reset(token)
