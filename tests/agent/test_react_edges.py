"""Tests for shared ReAct routing (tool budget vs ToolNode)."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.react_edges import (
    react_after_tools_decrement_budget,
    route_react_chat_to_tools,
    route_react_tools_next,
    tool_calls_batch_is_only_final_answer,
)


def test_tool_calls_batch_is_only_final_answer_true() -> None:
    tcs = [
        {"name": "final_answer", "args": {}, "id": "1", "type": "tool_call"},
    ]
    assert tool_calls_batch_is_only_final_answer(tcs) is True


def test_tool_calls_batch_is_only_final_answer_false_mixed() -> None:
    tcs = [
        {"name": "paper_profile", "args": {}, "id": "1", "type": "tool_call"},
        {"name": "final_answer", "args": {}, "id": "2", "type": "tool_call"},
    ]
    assert tool_calls_batch_is_only_final_answer(tcs) is False


def test_route_react_chat_to_tools_positive_budget() -> None:
    state = {
        "messages": [
            HumanMessage(content="hi"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"}
                ],
            ),
        ],
        "budget_remaining": 3,
    }
    assert route_react_chat_to_tools(state) == "tools"


def test_route_react_chat_to_tools_zero_budget_still_routes_to_tools() -> None:
    """Regression: last LLM hop at budget 0 must still execute pending tool_calls."""
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "paper_profile",
                        "args": {"work_id": "w1"},
                        "id": "b",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
        "budget_remaining": 0,
    }
    assert route_react_chat_to_tools(state) == "tools"


def test_route_react_chat_to_tools_negative_only_final_answer() -> None:
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "final_answer",
                        "args": {"answer": "done", "citations": []},
                        "id": "c",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
        "budget_remaining": -1,
    }
    assert route_react_chat_to_tools(state) == "tools"


def test_route_react_chat_to_tools_negative_minus_one_allows_grace_batch() -> None:
    """One extra tool batch at budget -1 so pending non-final tool_calls still execute."""
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "idea_search", "args": {"query": "q"}, "id": "d", "type": "tool_call"}
                ],
            ),
        ],
        "budget_remaining": -1,
    }
    assert route_react_chat_to_tools(state) == "tools"


def test_route_react_chat_to_tools_negative_blocks_non_final_below_minus_one() -> None:
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "idea_search", "args": {"query": "q"}, "id": "d", "type": "tool_call"}
                ],
            ),
        ],
        "budget_remaining": -2,
    }
    assert route_react_chat_to_tools(state) == END


def test_route_react_chat_to_tools_no_tool_calls() -> None:
    state = {
        "messages": [AIMessage(content="plain text only")],
        "budget_remaining": 5,
    }
    assert route_react_chat_to_tools(state) == END


def test_route_react_chat_to_tools_final_answer_nudge_after_catalog_tools() -> None:
    """P0: plain assistant text after a catalog tool must route to nudge, not END."""
    state = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Summary without final_answer tool."),
        ],
        "budget_remaining": 3,
        "workspace_id": "ws1",
        "metadata": {"raw_user_question": "q", "turn_policy": {"tool_policy": "allow_tools"}},
        "routing_log": [],
        "thread_id": None,
    }
    assert route_react_chat_to_tools(state) == "final_answer_nudge"


def test_route_react_chat_to_tools_second_nudge_after_legacy_used_flag() -> None:
    """Legacy ``final_answer_nudge_used`` without count still allows one more nudge (cap=2)."""
    state = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Still no tools after nudge."),
        ],
        "budget_remaining": 3,
        "workspace_id": "ws1",
        "metadata": {
            "raw_user_question": "q",
            "turn_policy": {"tool_policy": "allow_tools"},
            "final_answer_nudge_used": True,
        },
        "routing_log": [],
        "thread_id": None,
    }
    assert route_react_chat_to_tools(state) == "final_answer_nudge"


def test_route_react_chat_to_tools_nudge_suppressed_after_two_nudges() -> None:
    state = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Still no tools after two nudges."),
        ],
        "budget_remaining": 3,
        "workspace_id": "ws1",
        "metadata": {
            "raw_user_question": "q",
            "turn_policy": {"tool_policy": "allow_tools"},
            "final_answer_nudge_count": 2,
            "final_answer_nudge_used": True,
        },
        "routing_log": [],
        "thread_id": None,
    }
    assert route_react_chat_to_tools(state) == END


def test_react_after_tools_decrement_budget() -> None:
    out = react_after_tools_decrement_budget({"budget_remaining": 2})
    assert out["budget_remaining"] == 1
    assert out["metadata"]["react_prev_tool_batch_sigs"] == []


def test_react_after_tools_duplicate_batch_emits_debug_warning() -> None:
    tc = [{"name": "paper_profile", "args": {"work_id": "w1"}, "id": "a", "type": "tool_call"}]
    ai = AIMessage(content="", tool_calls=tc)
    tm = ToolMessage(content="{}", tool_call_id="a", name="paper_profile")
    first = react_after_tools_decrement_budget(
        {"budget_remaining": 3, "messages": [ai, tm], "metadata": {}}
    )
    assert first["budget_remaining"] == 2
    assert "debug_events" not in first or not first.get("debug_events")
    second = react_after_tools_decrement_budget(
        {
            "budget_remaining": 2,
            "messages": [ai, tm, ai, tm],
            "metadata": first["metadata"],
        }
    )
    assert second["budget_remaining"] == 1
    assert second.get("debug_events")
    assert second["debug_events"][0]["code"] == "duplicate_tool_batch_signature"


def test_react_after_tools_repeated_paper_profile_work_id_across_batches() -> None:
    """Warn when paper_profile repeats the same work_id after an intervening batch."""
    tc_pp = [{"name": "paper_profile", "args": {"work_id": "w1"}, "id": "a", "type": "tool_call"}]
    tc_other = [{"name": "idea_search", "args": {"query": "q"}, "id": "b", "type": "tool_call"}]
    ai1 = AIMessage(content="", tool_calls=tc_pp)
    tm1 = ToolMessage(content="{}", tool_call_id="a", name="paper_profile")
    ai2 = AIMessage(content="", tool_calls=tc_other)
    tm2 = ToolMessage(content="{}", tool_call_id="b", name="idea_search")
    ai3 = AIMessage(content="", tool_calls=tc_pp)
    tm3 = ToolMessage(content="{}", tool_call_id="a", name="paper_profile")

    m1 = react_after_tools_decrement_budget(
        {"budget_remaining": 5, "messages": [ai1, tm1], "metadata": {}}
    )
    assert m1.get("debug_events") in (None, [])
    m2 = react_after_tools_decrement_budget(
        {
            "budget_remaining": 4,
            "messages": [ai1, tm1, ai2, tm2],
            "metadata": m1["metadata"],
        }
    )
    m3 = react_after_tools_decrement_budget(
        {
            "budget_remaining": 3,
            "messages": [ai1, tm1, ai2, tm2, ai3, tm3],
            "metadata": m2["metadata"],
        }
    )
    assert m3.get("debug_events")
    codes = {e["code"] for e in m3["debug_events"]}
    assert "repeated_paper_profile_work_id" in codes


def test_react_after_tools_soft_cap_duplicate_tool_batch_sets_force_finalize() -> None:
    """3-й одинаковый батч (cap=2) -> ``react_force_finalize='duplicate_tool_batch'``."""
    tc = [{"name": "idea_search", "args": {"query": "q"}, "id": "a", "type": "tool_call"}]
    ai = AIMessage(content="", tool_calls=tc)
    tm = ToolMessage(content="{}", tool_call_id="a", name="idea_search")
    m1 = react_after_tools_decrement_budget(
        {"budget_remaining": 5, "messages": [ai, tm], "metadata": {}}
    )
    assert m1["metadata"].get("react_force_finalize") in (None, "")
    m2 = react_after_tools_decrement_budget(
        {
            "budget_remaining": 4,
            "messages": [ai, tm, ai, tm],
            "metadata": m1["metadata"],
        }
    )
    assert m2["metadata"].get("react_force_finalize") == "duplicate_tool_batch"
    codes = {e.get("code") for e in (m2.get("debug_events") or [])}
    assert "react_force_finalize" in codes


def test_react_after_tools_soft_cap_total_hops_sets_force_finalize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At ``react_total_hops`` >= cap -> ``react_force_finalize='react_hops_cap'``."""
    from science_graphrag.agent.graph import react_edges as edges_mod

    class _S:
        agent_react_max_consecutive_same_batch = 99
        agent_react_max_total_hops = 2

    monkeypatch.setattr(edges_mod, "get_settings", lambda: _S())

    tc1 = [{"name": "idea_search", "args": {"query": "q1"}, "id": "a", "type": "tool_call"}]
    tc2 = [{"name": "find_works", "args": {"query": "q2"}, "id": "b", "type": "tool_call"}]
    ai1 = AIMessage(content="", tool_calls=tc1)
    tm1 = ToolMessage(content="{}", tool_call_id="a", name="idea_search")
    ai2 = AIMessage(content="", tool_calls=tc2)
    tm2 = ToolMessage(content="{}", tool_call_id="b", name="find_works")

    m1 = react_after_tools_decrement_budget(
        {"budget_remaining": 5, "messages": [ai1, tm1], "metadata": {}}
    )
    assert m1["metadata"].get("react_total_hops") == 1
    assert m1["metadata"].get("react_force_finalize") in (None, "")
    m2 = react_after_tools_decrement_budget(
        {
            "budget_remaining": 4,
            "messages": [ai1, tm1, ai2, tm2],
            "metadata": m1["metadata"],
        }
    )
    assert m2["metadata"].get("react_total_hops") == 2
    assert m2["metadata"].get("react_force_finalize") == "react_hops_cap"


def test_react_after_tools_final_answer_only_does_not_count_hops() -> None:
    """``final_answer``-only batches do not bump ``react_total_hops`` or same-batch counter."""
    tc = [
        {
            "name": "final_answer",
            "args": {"answer": "done", "citations": []},
            "id": "f",
            "type": "tool_call",
        }
    ]
    ai = AIMessage(content="", tool_calls=tc)
    tm = ToolMessage(
        content='{"answer": "done", "citations": []}',
        tool_call_id="f",
        name="final_answer",
    )
    out = react_after_tools_decrement_budget(
        {"budget_remaining": 1, "messages": [ai, tm], "metadata": {}}
    )
    assert out["metadata"].get("react_total_hops", 0) == 0
    assert out["metadata"].get("react_consecutive_same_batch_count", 0) == 0
    assert out["metadata"].get("react_force_finalize") in (None, "")


def test_route_react_chat_to_tools_force_finalize_redirects_non_final_batch() -> None:
    """Soft-cap: non-final tool batch is redirected to ``final_answer_nudge``."""
    state = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "idea_search", "args": {"query": "q"}, "id": "x", "type": "tool_call"}
                ],
            ),
        ],
        "budget_remaining": 5,
        "metadata": {"react_force_finalize": "duplicate_tool_batch"},
    }
    assert route_react_chat_to_tools(state) == "final_answer_nudge"


def test_route_react_chat_to_tools_force_finalize_allows_final_answer_batch() -> None:
    """Soft-cap: ``final_answer``-only batches still go to tools so the writer closes the turn."""
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "final_answer",
                        "args": {"answer": "done", "citations": []},
                        "id": "f",
                        "type": "tool_call",
                    }
                ],
            ),
        ],
        "budget_remaining": 1,
        "metadata": {"react_force_finalize": "duplicate_tool_batch"},
    }
    assert route_react_chat_to_tools(state) == "tools"


def test_route_react_chat_to_tools_force_finalize_plain_text_goes_to_nudge() -> None:
    state = {
        "messages": [AIMessage(content="some text without tool_calls")],
        "budget_remaining": 2,
        "metadata": {"react_force_finalize": "react_hops_cap"},
    }
    assert route_react_chat_to_tools(state) == "final_answer_nudge"


def test_route_react_tools_next_force_finalize_no_final_answer_returns_end() -> None:
    """Soft-cap: after a ToolNode batch without ``final_answer`` we must not loop back to chat."""
    tc = [{"name": "idea_search", "args": {"query": "q"}, "id": "a", "type": "tool_call"}]
    ai = AIMessage(content="", tool_calls=tc)
    tm = ToolMessage(content="{}", tool_call_id="a", name="idea_search")
    state = {
        "messages": [ai, tm],
        "metadata": {"react_force_finalize": "duplicate_tool_batch"},
    }
    assert route_react_tools_next(state) == END


def test_route_react_tools_next_force_finalize_final_answer_ok_returns_end() -> None:
    tc = [
        {
            "name": "final_answer",
            "args": {"answer": "done", "citations": []},
            "id": "f",
            "type": "tool_call",
        }
    ]
    ai = AIMessage(content="", tool_calls=tc)
    tm = ToolMessage(
        content='{"answer": "done", "citations": []}',
        tool_call_id="f",
        name="final_answer",
    )
    state = {
        "messages": [ai, tm],
        "metadata": {"react_force_finalize": "react_hops_cap"},
    }
    assert route_react_tools_next(state) == END
