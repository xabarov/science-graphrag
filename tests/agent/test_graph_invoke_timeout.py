"""Wall-clock deadline for LangGraph invoke (sync path)."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.agent.graph.invoke_timeout import (
    graph_invoke_completed_after_deadline_total,
    invoke_graph_with_deadline,
    reset_agent_graph_executor_for_tests,
    set_graph_invoke_after_deadline_hook,
)
from science_graphrag.config import Settings


@pytest.fixture(autouse=True)
def _reset_agent_graph_pool() -> Any:
    reset_agent_graph_executor_for_tests()
    yield
    reset_agent_graph_executor_for_tests()


def test_invoke_graph_with_deadline_raises_when_slow() -> None:
    class _SlowGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            time.sleep(3.0)
            return {"ok": True}

    done = threading.Event()

    def _mark_done(_payload: dict[str, Any]) -> None:
        done.set()

    set_graph_invoke_after_deadline_hook(_mark_done)
    try:
        with pytest.raises(AgentGraphDeadlineExceeded):
            invoke_graph_with_deadline(
                _SlowGraph(),
                {},
                config={},
                timeout_seconds=0.2,
            )
        assert done.wait(timeout=5.0) is True
    finally:
        set_graph_invoke_after_deadline_hook(None)


def test_invoke_graph_with_deadline_zero_skips_pool() -> None:
    class _FastGraph:
        def invoke(self, state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            return {"echo": state.get("x")}

    out = invoke_graph_with_deadline(
        _FastGraph(),
        {"x": 1},
        config={},
        timeout_seconds=0.0,
    )
    assert out == {"echo": 1}


def test_invoke_graph_after_deadline_callback_and_counter() -> None:
    class _SlowGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            time.sleep(0.4)
            return {"ok": True}

    received: list[dict[str, Any]] = []

    def _hook(payload: dict[str, Any]) -> None:
        received.append(dict(payload))

    before = graph_invoke_completed_after_deadline_total()
    set_graph_invoke_after_deadline_hook(_hook)
    try:
        with pytest.raises(AgentGraphDeadlineExceeded):
            invoke_graph_with_deadline(
                _SlowGraph(),
                {},
                config={},
                timeout_seconds=0.05,
            )
        time.sleep(0.7)
    finally:
        set_graph_invoke_after_deadline_hook(None)

    assert len(received) == 1
    assert received[0]["timeout_seconds"] == 0.05
    assert float(received[0]["lag_seconds"]) >= 0.0
    assert graph_invoke_completed_after_deadline_total() == before + 1


def test_invoke_graph_respects_agent_graph_invoke_max_workers() -> None:
    """Pool worker count is fixed at first use when settings passed."""

    class _FastGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            return {"ok": True}

    s = Settings(agent_graph_invoke_max_workers=3)
    reset_agent_graph_executor_for_tests()
    invoke_graph_with_deadline(_FastGraph(), {}, config={}, timeout_seconds=5.0, settings=s)
    from science_graphrag.agent.graph import invoke_timeout as mod

    assert mod._AGENT_GRAPH_POOL is not None  # pylint: disable=protected-access
    assert mod._AGENT_GRAPH_POOL_WORKERS == 3  # pylint: disable=protected-access
