"""SSE vs sync tool_trace parity when stream emits full state values."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings


class _FakeGraph:
    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        tc_id = "call-1"
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        AIMessage(
                            content="",
                            tool_calls=[
                                {
                                    "name": "idea_search",
                                    "args": {"query": "x"},
                                    "id": tc_id,
                                    "type": "tool",
                                }
                            ],
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {
                "n": {
                    "messages": [
                        ToolMessage(
                            content=json.dumps({"row_count": 1}),
                            tool_call_id=tc_id,
                            name="idea_search",
                        )
                    ]
                }
            },
        )
        yield (
            "updates",
            {"n": {"messages": [AIMessage(content="done from stream")]}},
        )
        full = {
            "messages": [
                human,
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "idea_search", "args": {"query": "x"}, "id": tc_id, "type": "tool"}
                    ],
                ),
                ToolMessage(
                    content=json.dumps({"row_count": 1}), tool_call_id=tc_id, name="idea_search"
                ),
                AIMessage(content="done from stream"),
            ],
            "workspace_id": state.get("workspace_id"),
            "citations": [],
            "tool_trace": [],
            "budget_remaining": 7,
            "metadata": {},
            "specialist_results": {},
            "current_specialist": None,
            "routing_log": [{"from": "supervisor", "to": "retrieval_agent", "budget_left": 8}],
            "debug_events": [],
        }
        yield ("values", full)


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def test_sse_final_tool_trace_matches_collect_tool_trace(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    monkeypatch.setattr(agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraph())
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings(agent_enabled=True)
    client.app.dependency_overrides[get_stores] = lambda: type(
        "_S",
        (),
        {
            "neo4j": None,
            "qdrant_chunks": None,
            "qdrant_works": None,
            "qdrant_claims": None,
            "blob": None,
        },
    )()
    try:
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    trace = finals[0].get("tool_trace") or []
    tools = [t.get("tool") for t in trace if isinstance(t, dict)]
    assert "route_to_specialist" in tools
    assert "idea_search" in tools
