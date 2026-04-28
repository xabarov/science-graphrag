"""Tests for optional ToolMessage compaction."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, ToolMessage

from science_graphrag.agent.tool_message_compact import maybe_compact_agent_messages_for_react
from science_graphrag.config import Settings


def test_compact_disabled_returns_same_list(monkeypatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "k")
    s = Settings(agent_tool_history_compact_enabled=False)
    msgs = [HumanMessage(content="hi"), ToolMessage(content="x" * 9000, tool_call_id="1", name="t")]
    out = maybe_compact_agent_messages_for_react(msgs, settings=s)
    assert out[1].content == msgs[1].content


def test_compact_truncates_old_tool_messages(monkeypatch) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "k")
    s = Settings(
        agent_tool_history_compact_enabled=True,
        agent_tool_history_compact_keep_latest_tool_messages=1,
        agent_tool_history_compact_max_tool_chars=400,
    )
    big = "y" * 900
    msgs = [
        HumanMessage(content="q"),
        ToolMessage(content=big, tool_call_id="a", name="idea_search"),
        ToolMessage(content="ok", tool_call_id="b", name="paper_profile"),
    ]
    out = maybe_compact_agent_messages_for_react(msgs, settings=s)
    assert out[1].content.endswith("[tool_payload_truncated]")
    assert len(out[1].content) < len(big)
    assert out[2].content == "ok"
