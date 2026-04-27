"""SSE vs sync tool_trace parity when stream emits full state values."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.context.session_store import clear_session_store_for_tests
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
            "metadata": dict(state.get("metadata") or {}),
            "specialist_results": {
                "retrieval_agent": [
                    {
                        "bibliography": {
                            "format": "gost",
                            "entries": ["Author. Title // Journal. — 2020."],
                            "filtered_work_ids": ["orphan-id"],
                            "warnings": ["some_work_ids_filtered"],
                        }
                    }
                ]
            },
            "current_specialist": None,
            "routing_log": [{"from": "supervisor", "to": "retrieval_agent", "budget_left": 8}],
            "debug_events": [],
            "thread_id": state.get("thread_id"),
            "session_summary": str(state.get("session_summary") or ""),
            "answer_class": None,
            "history_digest": list(state.get("history_digest") or []),
        }
        yield ("values", full)


class _FakeGraphFinalAnswerToolOnly:
    """Writer calls the structured final_answer tool and never emits plain assistant text."""

    async def astream(self, state, config=None, **kwargs):  # noqa: ARG002
        human = state["messages"][0]
        tc_id = "call-final"
        ai = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "final_answer",
                    "args": {"answer": "ok from tool", "citations": []},
                    "id": tc_id,
                    "type": "tool",
                }
            ],
        )
        tool = ToolMessage(
            content=json.dumps({"answer": "ok from tool", "citations": []}),
            tool_call_id=tc_id,
            name="final_answer",
        )
        yield ("updates", {"writer": {"messages": [ai]}})
        yield ("updates", {"writer": {"messages": [tool]}})
        yield (
            "values",
            {
                "messages": [human, ai, tool],
                "workspace_id": state.get("workspace_id"),
                "citations": [{"work_id": "should_be_replaced"}],
                "tool_trace": [],
                "budget_remaining": 1,
                "metadata": dict(state.get("metadata") or {}),
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [{"from": "supervisor", "to": "writer_agent", "budget_left": 1}],
                "debug_events": [],
                "thread_id": state.get("thread_id"),
                "session_summary": str(state.get("session_summary") or ""),
                "answer_class": None,
                "history_digest": list(state.get("history_digest") or []),
            },
        )


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def test_sse_final_tool_trace_matches_collect_tool_trace(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    monkeypatch.setattr(agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraph())
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings()
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

    types = [e.get("type") for e in events]
    assert "intent_classified" in types
    assert types.index("intent_classified") < types.index("specialist_selected")
    assert types.index("specialist_selected") < types.index("subagent_started")
    assert types.index("answer_synthesis_started") < types.index("final_answer")
    assert types.index("answer_synthesis_finished") < types.index("final_answer")
    assert "subagent_progress" in types or "tool_call" in types

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    trace = finals[0].get("tool_trace") or []
    tools = [t.get("tool") for t in trace if isinstance(t, dict)]
    assert "coordinator_gate" in tools
    assert "route_to_specialist" in tools
    assert "idea_search" in tools
    fa = finals[0]
    assert "some_work_ids_filtered" in (fa.get("warnings") or [])
    bib = fa.get("bibliography") or {}
    assert bib.get("filtered_work_ids") == ["orphan-id"]
    rm = fa.get("run_metadata") or {}
    assert "agent_runtime" in rm
    assert "extraction_llm_model" in rm


def test_sse_final_answer_uses_structured_final_answer_tool(monkeypatch) -> None:
    """SSE final event must not lose answers returned via the final_answer tool."""
    from science_graphrag.api import agent_v2 as agent_v2_api

    monkeypatch.setattr(
        agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraphFinalAnswerToolOnly()
    )
    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings()
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
    assert finals[0].get("answer") == "ok from tool"
    assert finals[0].get("citations") == []


def test_sse_context_compacted_and_session_init_with_thread(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraph())
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q", "thread_id": "thr_sse_parity"},
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
        clear_session_store_for_tests()

    types = [e.get("type") for e in events]
    assert "context_compacted" in types
    compact = next(e for e in events if e.get("type") == "context_compacted")
    assert compact.get("compaction", {}).get("kind") == "turn_digest"
    assert compact.get("compaction", {}).get("trigger") == "post_answer"
    assert "kinds" in compact.get("compaction", {})
    assert "turn_digest" in compact["compaction"]["kinds"]
    assert "digest_count" in compact.get("compaction", {})
    assert compact["compaction"].get("boundary", {}).get("status") == "idle"
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    trace = finals[0].get("tool_trace") or []
    tools = [t.get("tool") for t in trace if isinstance(t, dict)]
    assert "session_init" in tools
    assert finals[0].get("thread_id") == "thr_sse_parity"


def test_sse_history_digest_invalid_warning_and_final(monkeypatch) -> None:
    """SSE emits warning after intent_classified and history_digest_invalid on final_answer."""
    from science_graphrag.api import agent_v2 as agent_v2_api

    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraph())
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={
                "question": "q",
                "thread_id": "thr_digest_warn",
                "history_digest": "{not-json",
            },
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
        clear_session_store_for_tests()

    warns = [e for e in events if e.get("type") == "warning"]
    assert any(w.get("code") == "history_digest_invalid" for w in warns)
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert "history_digest_invalid" in (finals[0].get("warnings") or [])


class _FakeGraphUpdatesOnly:
    """Stream updates only (no ``values`` chunk) — exercises degraded compaction trigger."""

    async def astream(self, state, config=None, **_kwargs):  # noqa: ARG002
        assert isinstance(state, dict)
        yield (
            "updates",
            {"n": {"messages": [AIMessage(content="answer without values chunk")]}},
        )


def test_sse_context_compacted_degraded_trigger_without_values(monkeypatch) -> None:
    """``context_compacted`` uses degraded trigger when graph never yields ``values``."""
    from science_graphrag.api import agent_v2 as agent_v2_api

    try:
        clear_session_store_for_tests()
        monkeypatch.setattr(
            agent_v2_api, "build_retrieval_graph", lambda *_a, **_k: _FakeGraphUpdatesOnly()
        )
        client = TestClient(_app())
        client.app.dependency_overrides[get_settings] = lambda: Settings()
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
        events = []
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "q", "thread_id": "thr_no_values"},
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
        clear_session_store_for_tests()

    compact = next((e for e in events if e.get("type") == "context_compacted"), {})
    assert compact.get("compaction", {}).get("trigger") == "post_answer_degraded_stream"
    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert finals[0].get("answer") == "answer without values chunk"
