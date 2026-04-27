"""Tests for shared ReAct subgraph routing (post-tool termination)."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import END

from science_graphrag.agent.graph.react_edges import route_react_tools_next
from science_graphrag.agent.graph.state import AgentState


def _minimal_state(messages: list) -> AgentState:
    return {
        "messages": messages,
        "workspace_id": None,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
        "thread_id": None,
        "session_summary": "",
        "answer_class": None,
        "history_digest": [],
    }


def test_route_after_tools_ends_on_final_answer_tool_message() -> None:
    msgs = [
        HumanMessage(content="hi"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "t1", "args": {"answer": "done", "citations": []}}
            ],
        ),
        ToolMessage(content='{"ok": true}', name="final_answer", tool_call_id="t1"),
    ]
    assert route_react_tools_next(_minimal_state(msgs)) == END


def test_route_after_tools_loops_to_chat_when_last_tool_not_final() -> None:
    msgs = [
        HumanMessage(content="hi"),
        AIMessage(
            content="",
            tool_calls=[{"name": "idea_search", "id": "t1", "args": {"query": "x"}}],
        ),
        ToolMessage(content="{}", name="idea_search", tool_call_id="t1"),
    ]
    assert route_react_tools_next(_minimal_state(msgs)) == "chat"


def test_route_after_tools_ends_if_final_answer_appears_in_tool_batch() -> None:
    msgs = [
        HumanMessage(content="hi"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "idea_search", "id": "t1", "args": {"query": "x"}},
                {"name": "final_answer", "id": "t2", "args": {"answer": "z", "citations": []}},
            ],
        ),
        ToolMessage(content="{}", name="idea_search", tool_call_id="t1"),
        ToolMessage(content='{"ok": true}', name="final_answer", tool_call_id="t2"),
    ]
    assert route_react_tools_next(_minimal_state(msgs)) == END
