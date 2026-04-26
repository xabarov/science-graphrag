"""Tests for LangGraph answer extraction (final_answer tool vs bare AIMessage)."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.runtime import extract_langgraph_answer


def test_extract_prefers_final_answer_tool_payload() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "x", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "Structured reply", "citations": [{"work_id": "w1"}]}),
            tool_call_id="c1",
        ),
    ]
    answer, cites = extract_langgraph_answer(msgs)
    assert answer == "Structured reply"
    assert cites == [{"work_id": "w1"}]


def test_extract_uses_final_answer_tool_args_when_tool_message_missing() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "id": "c1",
                    "args": {"answer": "Structured reply from args", "citations": []},
                }
            ],
        ),
    ]
    answer, cites = extract_langgraph_answer(msgs)
    assert answer == "Structured reply from args"
    assert cites == []


def test_extract_falls_back_to_plain_assistant() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="Plain reply without tools"),
    ]
    answer, cites = extract_langgraph_answer(msgs)
    assert answer == "Plain reply without tools"
    assert cites is None
