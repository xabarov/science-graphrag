"""Tests for per-request agent turn policy (web toggle, plan mode session hints)."""

from __future__ import annotations

from science_graphrag.agent.request_turn_policy import (
    build_agent_request_turn_context,
    compute_turn_tool_denylist,
    effective_web_research_user_enabled,
)
from science_graphrag.config import Settings


def test_effective_web_research_user_enabled_none_is_true() -> None:
    assert effective_web_research_user_enabled(None) is True
    assert effective_web_research_user_enabled(True) is True
    assert effective_web_research_user_enabled(False) is False


def test_compute_turn_tool_denylist_when_deploy_on_user_off() -> None:
    st = Settings.model_construct(agent_web_research_tools_enabled=True)
    assert compute_turn_tool_denylist(st, web_research_user_enabled=False) == [
        "web_fetch",
        "web_search",
    ]


def test_compute_turn_tool_denylist_deploy_off() -> None:
    st = Settings.model_construct(agent_web_research_tools_enabled=False)
    assert compute_turn_tool_denylist(st, web_research_user_enabled=False) == []


def test_build_agent_request_turn_context_metadata_keys() -> None:
    st = Settings.model_construct(agent_web_research_tools_enabled=True)
    ctx = build_agent_request_turn_context(
        st,
        thread_id=None,
        web_research_enabled=False,
        agent_mode="agent",
    )
    assert ctx.turn_tool_denylist
    assert ctx.run_metadata_fragment.get("effective_web_research_tools") is False
