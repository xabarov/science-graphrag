"""Wall-clock deadline for LangGraph invoke (sync path)."""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest
from langgraph.errors import GraphRecursionError

from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
    telemetry_max_tool_calls_from_state,
)
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


def test_telemetry_max_tool_calls_prefers_metadata_over_budget_remaining() -> None:
    """Span ``agent.max_tool_calls`` must reflect configured budget, not remaining slots."""

    state = {"budget_remaining": 3, "metadata": {"agent_max_tool_calls": 12}}
    assert telemetry_max_tool_calls_from_state(state) == 12


def test_invoke_graph_wraps_graph_recursion_error_into_domain_exception() -> None:
    """``GraphRecursionError`` from the worker becomes ``AgentGraphRecursionLimitExceeded``."""

    class _RecursingGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            raise GraphRecursionError("Recursion limit reached")

    with pytest.raises(AgentGraphRecursionLimitExceeded) as info:
        invoke_graph_with_deadline(
            _RecursingGraph(),
            {"metadata": {"agent_runtime": "langgraph_research_v1"}},
            config={"recursion_limit": 64},
            timeout_seconds=5.0,
        )
    assert info.value.recursion_limit == 64
    assert info.value.latest_state is None


def test_invoke_graph_zero_timeout_also_wraps_graph_recursion_error() -> None:
    class _RecursingGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            raise GraphRecursionError("Recursion limit reached zero")

    with pytest.raises(AgentGraphRecursionLimitExceeded) as info:
        invoke_graph_with_deadline(
            _RecursingGraph(),
            {},
            config={"recursion_limit": 32},
            timeout_seconds=0.0,
        )
    assert info.value.recursion_limit == 32


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
