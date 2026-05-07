"""Tests for LangGraph answer extraction (final_answer tool vs bare AIMessage)."""

from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.runtime import (
    extract_langgraph_answer,
    salvage_markdown_from_quote_candidates,
)


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
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert answer == "Structured reply"
    assert cites == [{"work_id": "w1"}]
    assert graph_sv is False
    assert draft_sv is False


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
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert answer == "Structured reply from args"
    assert cites == []
    assert graph_sv is False
    assert draft_sv is False


def test_extract_falls_back_to_plain_assistant() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="Plain reply without tools"),
    ]
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert answer == "Plain reply without tools"
    assert cites is None
    assert graph_sv is False
    assert draft_sv is False


def test_extract_salvages_from_cypher_error_payload() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "cypher_query", "id": "c1", "args": {"query": "RETURN 1"}},
            ],
        ),
        ToolMessage(
            content=json.dumps({"error": "Label X not allowed", "rows": []}),
            tool_call_id="c1",
            name="cypher_query",
        ),
    ]
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert graph_sv is True
    assert draft_sv is False
    assert "Cypher error" in answer
    assert "Label X not allowed" in answer
    assert cites is None


def test_extract_salvages_from_cypher_tool_when_no_bare_ai() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "cypher_query", "id": "c1", "args": {"query": "RETURN 1 AS n"}},
            ],
        ),
        ToolMessage(
            content=json.dumps({"rows": [{"n": 1}], "row_count": 1}),
            tool_call_id="c1",
            name="cypher_query",
        ),
    ]
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert graph_sv is True
    assert draft_sv is False
    assert "Cypher returned" in answer
    assert cites is None


def test_extract_salvages_visible_ai_when_final_answer_json_answer_empty() -> None:
    """Writer may emit final_answer with empty JSON answer but non-empty reasoning in AIMessage."""
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content="CHECK_TURN_1",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "", "citations": []}}
            ],
        ),
        ToolMessage(
            content=json.dumps({"answer": "", "citations": []}),
            tool_call_id="c1",
            name="final_answer",
        ),
    ]
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert answer == "CHECK_TURN_1"
    assert cites is None
    assert graph_sv is False
    assert draft_sv is False


def test_extract_salvages_long_visible_ai_content_with_tool_calls() -> None:
    long_body = "x" * 220
    msgs = [
        HumanMessage(content="q"),
        AIMessage(
            content=long_body,
            tool_calls=[
                {"name": "find_works", "id": "a", "args": {"query": "y"}, "type": "tool_call"},
            ],
        ),
        ToolMessage(content="{}", tool_call_id="a", name="find_works"),
    ]
    answer, cites, graph_sv, draft_sv = extract_langgraph_answer(msgs)
    assert answer == long_body
    assert cites is None
    assert graph_sv is False
    assert draft_sv is True


def test_salvage_markdown_from_quote_candidates() -> None:
    state = {
        "specialist_results": {
            "retrieval_agent": [
                {"quote_candidates": [{"quote_text": "line1\nline2", "work_id": "w-1"}]},
            ],
        },
    }
    out = salvage_markdown_from_quote_candidates(state)
    assert "w-1" in out
    assert "> line1" in out
    assert "> line2" in out
