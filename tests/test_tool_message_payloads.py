"""Typed payloads from ``ToolMessage`` bodies (single-agent evidence path)."""

from __future__ import annotations

import json

from langchain_core.messages import ToolMessage

from science_graphrag.agent.tool_message_payloads import typed_payloads_from_tool_messages


def test_quote_candidates_from_paper_quote_search_message() -> None:
    msgs = [
        ToolMessage(
            content=json.dumps(
                {
                    "row_count": 2,
                    "quote_candidates": [{"work_id": "w1", "quote_text": "x"}],
                }
            ),
            tool_call_id="c1",
            name="paper_quote_search",
        ),
    ]
    out = typed_payloads_from_tool_messages(msgs)
    assert len(out.get("quote_candidates") or []) == 1


def test_web_sources_merged_from_tool_messages() -> None:
    msgs = [
        ToolMessage(
            content=json.dumps(
                {
                    "ok": True,
                    "row_count": 1,
                    "web_sources": [
                        {
                            "title": "Paper",
                            "url": "https://doi.org/10.1/x",
                            "doi": "10.1/x",
                            "source_tool": "web_search",
                            "snippet": "",
                        }
                    ],
                }
            ),
            tool_call_id="c2",
            name="web_search",
        ),
    ]
    out = typed_payloads_from_tool_messages(msgs)
    ws = out.get("web_sources") or []
    assert len(ws) == 1
    assert ws[0].get("url") == "https://doi.org/10.1/x"
