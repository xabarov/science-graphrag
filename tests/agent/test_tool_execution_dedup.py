from __future__ import annotations

import json

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.tool_call_dedup import normalize_web_fetch_url
from science_graphrag.agent.tool_execution_pipeline import build_tool_execution_node
from science_graphrag.config import Settings


def test_tool_execution_dedup_suppresses_second_identical_web_fetch() -> None:
    url = "https://example.org/same"

    @tool("web_fetch")
    def web_fetch(url: str) -> dict:
        """Fetch URL."""
        return {"ok": True, "url": url}

    settings = Settings.model_construct(agent_per_tool_call_timeout_seconds=0.0)
    state = build_initial_agent_state(
        question="fetch",
        workspace_id=None,
        max_tool_calls=8,
        agent_runtime="langgraph_research_v1",
        settings=settings,
    )
    node = build_tool_execution_node(tools=[web_fetch], settings=settings)
    ai = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_fetch", "id": "c1", "args": {"url": url}},
            {"name": "web_fetch", "id": "c2", "args": {"url": url}},
        ],
    )
    out = node({**state, "messages": [ai]}, None)
    msgs = list(out.get("messages") or [])
    assert len(msgs) == 1
    assert isinstance(msgs[0], ToolMessage)
    dedup_events = [
        e for e in out.get("debug_events") or [] if e.get("type") == "tool_dedup_suppressed"
    ]
    assert len(dedup_events) == 1
    norm = normalize_web_fetch_url({"url": url})
    assert norm in (out.get("metadata") or {}).get("turn_web_fetch_urls") or []


def test_tool_execution_dedup_all_duplicates_returns_suppression_messages() -> None:
    url = "https://example.org/only"
    norm = normalize_web_fetch_url({"url": url})
    assert norm is not None

    @tool("web_fetch")
    def web_fetch(url: str) -> dict:
        """Fetch URL."""
        return {"ok": True, "url": url}

    settings = Settings.model_construct(agent_per_tool_call_timeout_seconds=0.0)
    state = build_initial_agent_state(
        question="fetch",
        workspace_id=None,
        max_tool_calls=8,
        agent_runtime="langgraph_research_v1",
        settings=settings,
    )
    meta = dict(state.get("metadata") or {})
    meta["turn_web_fetch_urls"] = [norm]
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "web_fetch", "id": "c2", "args": {"url": url}}],
    )
    node = build_tool_execution_node(tools=[web_fetch], settings=settings)
    out = node({**state, "metadata": meta, "messages": [ai]}, None)
    msgs = list(out.get("messages") or [])
    assert len(msgs) == 1
    body = json.loads(str(msgs[0].content))
    assert body.get("error") == "duplicate_identical_fetch"
