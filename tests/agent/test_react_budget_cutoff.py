"""Cooperative agent response-budget cutoff (Phase 4)."""

from __future__ import annotations

from time import perf_counter

from science_graphrag.agent.graph.react_edges import react_chat_response_budget_cutoff
from science_graphrag.config import Settings


def test_react_chat_response_budget_cutoff_triggers_when_below_reserve() -> None:
    settings = Settings(agent_step_timeout_seconds=60.0, agent_min_llm_hop_reserve_seconds=1.0)
    state = {
        "metadata": {
            "agent_response_deadline_perf_start": perf_counter() - 100.0,
            "agent_response_deadline_seconds": 60.0,
        }
    }
    out = react_chat_response_budget_cutoff(state, settings=settings)
    assert out is not None
    assert "messages" in out
    ev = out.get("debug_events") or []
    assert any(isinstance(e, dict) and e.get("code") == "agent_response_budget_cutoff" for e in ev)


def test_react_chat_response_budget_cutoff_skips_when_enough_time() -> None:
    settings = Settings(agent_step_timeout_seconds=60.0, agent_min_llm_hop_reserve_seconds=1.0)
    state = {
        "metadata": {
            "agent_response_deadline_perf_start": perf_counter() - 1.0,
            "agent_response_deadline_seconds": 60.0,
        }
    }
    assert react_chat_response_budget_cutoff(state, settings=settings) is None
