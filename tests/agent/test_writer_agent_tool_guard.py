from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.nodes.writer_agent import (
    _drop_non_final_tool_calls_from_tail,
    _ensure_final_answer_tool,
    _is_generic_writer_fallback_text,
    _synthesize_partial_answer_from_context,
    _ensure_terminal_final_answer_tool_call,
)
from science_graphrag.agent.tools import build_writer_tools


def _tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def test_ensure_final_answer_tool_appends_when_missing() -> None:
    shortlisted = [_tool("workspace_inspect")]
    all_tools = [_tool("workspace_inspect"), _tool("final_answer")]
    out = _ensure_final_answer_tool(shortlisted, all_tools)
    assert [t.name for t in out] == ["workspace_inspect", "final_answer"]


def test_ensure_final_answer_tool_keeps_existing_order() -> None:
    shortlisted = [_tool("final_answer"), _tool("workspace_inspect")]
    all_tools = [_tool("final_answer"), _tool("workspace_inspect")]
    out = _ensure_final_answer_tool(shortlisted, all_tools)
    assert [t.name for t in out] == ["final_answer", "workspace_inspect"]


def test_writer_bare_text_gets_synthetic_final_answer_tool_call() -> None:
    msgs = [AIMessage(content="final_answer:\nHello from writer")]
    out = _ensure_terminal_final_answer_tool_call(msgs, citations=[{"work_id": "w1"}])
    assert len(out) == 3
    assert isinstance(out[-2], AIMessage)
    assert isinstance(out[-1], ToolMessage)
    payload = json.loads(str(out[-1].content))
    assert payload["answer"] == "Hello from writer"
    assert payload["citations"] == [{"work_id": "w1"}]


def test_build_writer_tools_catalog_is_final_answer_only() -> None:
    tools = build_writer_tools(MagicMock())
    assert [getattr(t, "name", "") for t in tools] == ["final_answer"]


def test_existing_final_answer_tool_call_is_not_duplicated() -> None:
    msgs = [
        AIMessage(
            content="",
            tool_calls=[
                {"name": "final_answer", "id": "c1", "args": {"answer": "Done", "citations": []}}
            ],
        ),
        ToolMessage(content=json.dumps({"answer": "Done", "citations": []}), tool_call_id="c1"),
    ]
    out = _ensure_terminal_final_answer_tool_call(msgs)
    assert out == msgs


def test_drop_non_final_tool_calls_from_tail_for_writer_terminal() -> None:
    msgs = [
        AIMessage(content="intermediate synthesis"),
        AIMessage(
            content="",
            tool_calls=[
                {"name": "arxiv_search", "id": "c2", "args": {"query": "sam"}, "type": "tool_call"}
            ],
        ),
    ]
    out = _drop_non_final_tool_calls_from_tail(msgs)
    assert len(out) == 1
    assert isinstance(out[0], AIMessage)
    assert not getattr(out[0], "tool_calls", None)


def test_generic_writer_fallback_detection() -> None:
    assert _is_generic_writer_fallback_text(
        "I could not produce a complete final answer for this turn. Please rephrase."
    )
    assert not _is_generic_writer_fallback_text("Partial grounded answer based on evidence.")


def test_synthesize_partial_answer_from_context_ru() -> None:
    text = _synthesize_partial_answer_from_context(
        citations=[{"url": "https://example.org/a"}],
        specialist_results_v3={
            "merge": {
                "completion_state": "evidence_insufficient",
                "writer_directive": "PDF_UNAVAILABLE: no safe candidate",
            }
        },
        language="ru",
    )
    assert "Промежуточный результат" in text
    assert "completion_state: evidence_insufficient" in text
    assert "получено источников: 1" in text


def test_terminal_final_answer_fallback_replaces_generic_with_partial_when_citations_present() -> None:
    msgs = [
        AIMessage(
            content="I could not produce a complete final answer for this turn. Please rephrase."
        )
    ]
    out = _ensure_terminal_final_answer_tool_call(
        msgs,
        citations=[{"url": "https://example.org/a"}],
        specialist_results_v3={"merge": {"completion_state": "any_specialist_payload"}},
        answer_language="ru",
    )
    assert len(out) == 3
    payload = json.loads(str(out[-1].content))
    assert "Промежуточный результат" in payload["answer"]
    assert payload["citations"] == [{"url": "https://example.org/a"}]
