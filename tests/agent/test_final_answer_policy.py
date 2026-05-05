"""Tests for ``science_graphrag.agent.final_answer_policy``."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.final_answer_policy import (
    effective_final_answer_nudge_count,
    has_completed_final_answer_tool,
    last_executed_catalog_tool_name,
    needs_final_answer_nudge,
)
from science_graphrag.agent.graph.state import AgentState


def _minimal_state(**kwargs: object) -> AgentState:
    base: AgentState = {
        "messages": [],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {"raw_user_question": "q", "turn_policy": {"tool_policy": "allow_tools"}},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }
    base.update(kwargs)
    return base


def test_last_executed_catalog_tool_name_skips_meta() -> None:
    trace = [
        {"tool": "coordinator_gate"},
        {"tool": "find_works"},
        {"tool": "paper_profile"},
    ]
    assert last_executed_catalog_tool_name(trace) == "paper_profile"


def test_has_completed_final_answer_tool_true() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "x", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "Done", "citations": []}),
            tool_call_id="c1",
            name="final_answer",
        ),
    ]
    assert has_completed_final_answer_tool(msgs) is True


def test_needs_final_answer_nudge_after_tools_then_plain_ai() -> None:
    state = _minimal_state(
        messages=[
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Stopping without calling final_answer."),
        ],
    )
    assert needs_final_answer_nudge(state) is True


def test_needs_final_answer_nudge_true_when_legacy_used_without_count() -> None:
    """One historical nudge (``used`` only) still allows a second reminder."""
    state = _minimal_state(
        metadata={
            "raw_user_question": "q",
            "turn_policy": {"tool_policy": "allow_tools"},
            "final_answer_nudge_used": True,
        },
        messages=[
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Still no tools."),
        ],
    )
    assert needs_final_answer_nudge(state) is True


def test_needs_final_answer_nudge_false_when_max_nudges_reached() -> None:
    state = _minimal_state(
        metadata={
            "raw_user_question": "q",
            "turn_policy": {"tool_policy": "allow_tools"},
            "final_answer_nudge_count": 2,
            "final_answer_nudge_used": True,
        },
        messages=[
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(content="Still no tools."),
        ],
    )
    assert needs_final_answer_nudge(state) is False


def test_effective_final_answer_nudge_count_prefers_integer() -> None:
    meta = {"final_answer_nudge_count": 2, "final_answer_nudge_used": True}
    assert effective_final_answer_nudge_count(meta) == 2


def test_needs_final_answer_nudge_false_plain_first_turn() -> None:
    state = _minimal_state(
        messages=[HumanMessage(content="q"), AIMessage(content="Plain only.")],
    )
    assert needs_final_answer_nudge(state) is False


def test_needs_final_answer_nudge_true_when_final_answer_tool_failed_then_plain_ai() -> None:
    """Incomplete ``final_answer`` must not block a further nudge (trace last tool can be final_answer)."""

    state = _minimal_state(
        messages=[
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "args": {"query": "x"}, "id": "a", "type": "tool_call"},
                ],
            ),
            ToolMessage(content="{}", tool_call_id="a", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "final_answer",
                        "id": "b",
                        "type": "tool_call",
                        "args": {"answer": "", "citations": []},
                    },
                ],
            ),
            ToolMessage(
                content=json.dumps({"answer": "", "citations": []}),
                tool_call_id="b",
                name="final_answer",
            ),
            AIMessage(content="Still prose only."),
        ],
    )
    assert has_completed_final_answer_tool(list(state["messages"])) is False
    assert needs_final_answer_nudge(state) is True


def test_needs_final_answer_nudge_false_after_completed_final_answer() -> None:
    state = _minimal_state(
        messages=[
            HumanMessage(content="q"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "final_answer",
                        "id": "c1",
                        "args": {"answer": "Done", "citations": []},
                    },
                ],
            ),
            ToolMessage(
                content=json.dumps({"answer": "Done", "citations": []}),
                tool_call_id="c1",
                name="final_answer",
            ),
            AIMessage(content="Plain follow-up."),
        ],
    )
    assert needs_final_answer_nudge(state) is False
