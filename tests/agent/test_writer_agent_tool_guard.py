from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.nodes.writer_agent import (
    _ensure_final_answer_tool,
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
