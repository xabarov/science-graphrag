"""Tests for LangGraph message → tool payload extraction helpers."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from science_graphrag.agent.graph.tracing import (
    extract_last_ok_tool_payload,
    extract_last_tool_payload_for_tool,
)


def test_extract_last_tool_payload_includes_failed_ok_false() -> None:
    messages = [
        ToolMessage(
            content=json.dumps(
                {"ok": False, "artifact_id": "sg-pdf-1", "error": "blocked"}
            ),
            tool_call_id="a",
            name="read_external_pdf",
        )
    ]
    pl = extract_last_tool_payload_for_tool(messages, tool="read_external_pdf")
    assert pl is not None
    assert pl.get("ok") is False
    assert pl.get("artifact_id") == "sg-pdf-1"
    assert extract_last_ok_tool_payload(messages, tool="read_external_pdf") is None


def test_extract_last_tool_payload_prefers_last_matching_message() -> None:
    messages = [
        ToolMessage(
            content=json.dumps({"ok": True, "artifact_id": "old"}),
            tool_call_id="1",
            name="read_external_pdf",
        ),
        ToolMessage(
            content=json.dumps({"ok": False, "artifact_id": "new", "error": "x"}),
            tool_call_id="2",
            name="read_external_pdf",
        ),
    ]
    pl = extract_last_tool_payload_for_tool(messages, tool="read_external_pdf")
    assert pl.get("artifact_id") == "new"
