"""Wall-clock deadline for LangGraph invoke (sync path)."""

from __future__ import annotations

import time

import pytest

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline


def test_invoke_graph_with_deadline_raises_when_slow() -> None:
    class _SlowGraph:
        def invoke(self, _state: dict, config: dict | None = None) -> dict:  # noqa: ARG002
            time.sleep(3.0)
            return {"ok": True}

    with pytest.raises(AgentGraphDeadlineExceeded):
        invoke_graph_with_deadline(
            _SlowGraph(),
            {},
            config={},
            timeout_seconds=0.2,
        )


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
