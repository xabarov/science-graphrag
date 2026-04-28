"""Tests for shared ReAct routing (tool budget vs ToolNode)."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.react_edges import (
    react_after_tools_decrement_budget,
    route_react_chat_to_tools,
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


def test_route_react_chat_to_tools_negative_blocks_other_tools() -> None:
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


def test_route_react_chat_to_tools_nudge_suppressed_after_flag() -> None:
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
