"""Routing after ToolNode: ``final_answer`` must carry non-empty ``answer`` JSON to finish."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.react_edges import (
    _MAX_FINAL_ANSWER_EMPTY_REPAIR_HOPS,
    final_answer_tool_message_ok,
    route_react_tools_next,
)
from science_graphrag.agent.graph.state import AgentState


def _state_with_messages(messages: list, *, hops: int = 0) -> AgentState:
    meta: dict = {"raw_user_question": "q"}
    if hops:
        meta["final_answer_empty_repair_hops"] = hops
    return {
        "messages": messages,
        "workspace_id": "ws",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 0,
        "metadata": meta,
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }


def test_final_answer_tool_message_ok_accepts_nonempty() -> None:
    msg = ToolMessage(
        content=json.dumps({"answer": "Hello", "citations": []}),
        tool_call_id="t1",
        name="final_answer",
    )
    assert final_answer_tool_message_ok(msg) is True


def test_final_answer_tool_message_ok_rejects_empty_answer() -> None:
    msg = ToolMessage(
        content=json.dumps({"answer": "  ", "citations": []}),
        tool_call_id="t1",
        name="final_answer",
    )
    assert final_answer_tool_message_ok(msg) is False


def test_route_ends_when_final_answer_payload_ok() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "X", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "Done", "citations": []}),
            tool_call_id="c1",
            name="final_answer",
        ),
    ]
    out = route_react_tools_next(_state_with_messages(msgs))
    assert out is END


def test_route_returns_chat_on_invalid_final_answer_when_under_repair_cap() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "bad", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "", "citations": []}),
            tool_call_id="c1",
            name="final_answer",
        ),
    ]
    out = route_react_tools_next(_state_with_messages(msgs, hops=0))
    assert out == "chat"


def test_route_ends_after_excess_repair_hops_even_if_final_still_bad() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "bad", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "", "citations": []}),
            tool_call_id="c1",
            name="final_answer",
        ),
    ]
    hops = _MAX_FINAL_ANSWER_EMPTY_REPAIR_HOPS + 1
    out = route_react_tools_next(_state_with_messages(msgs, hops=hops))
    assert out is END


def test_route_returns_chat_when_latest_batch_has_no_final_answer_tool() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[{"name": "find_works", "id": "c1", "args": {"query": "x"}}],
        ),
        ToolMessage(
            content=json.dumps({"row_count": 1, "items": []}),
            tool_call_id="c1",
            name="find_works",
        ),
    ]
    assert route_react_tools_next(_state_with_messages(msgs)) == "chat"
