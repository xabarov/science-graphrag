"""Smoke tests for POST /v2/agent/query (Wave Y3)."""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from science_graphrag.api.agent import router as agent_router
from science_graphrag.api.agent_v2 import router as agent_v2_router
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings

_EMPTY_STORES = type(
    "_EmptyStores",
    (),
    {
        "neo4j": None,
        "qdrant_chunks": None,
        "qdrant_works": None,
        "qdrant_claims": None,
        "blob": None,
    },
)()


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_router, prefix="/v1")
    app.include_router(agent_v2_router, prefix="/v2")
    return app


def test_v2_sync_json(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _FakeOut:
        answer = "Test answer"
        citations = [{"work_id": "w1", "title": "Test Work"}]
        tool_trace = [{"step": 1, "tool": "entity_search", "args_summary": {"query": "test"}}]

    class _FakeAgent:
        def run(self, **_kwargs):
            return _FakeOut()

    monkeypatch.setattr(agent_v2_api, "build_agent", lambda **_kwargs: _FakeAgent())
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        resp = client.post(
            "/v2/agent/query",
            json={"question": "What is BERT?"},
            headers={"Accept": "application/json"},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["answer"] == "Test answer"
    assert "phoenix_trace_id" in data
    assert "tool_trace" in data


def test_v2_sse_stream(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _FakeGraph:
        async def astream(self, _state, config=None):  # noqa: ARG002
            yield {"chat": {"messages": [AIMessage(content="Streamed final answer")]}}

    monkeypatch.setattr(
        agent_v2_api, "build_retrieval_graph", lambda *_args, **_kwargs: _FakeGraph()
    )
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "What is BERT?"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    types = [event["type"] for event in events]
    assert "final_answer" in types


def test_v2_sse_stream_formats_provider_valueerror(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    class _BrokenGraph:
        async def astream(self, _state, config=None):  # noqa: ARG002
            # Must yield once so ``astream`` is an async generator (not a plain coroutine).
            yield {"chat": {"messages": []}}
            raise ValueError({"message": "Provider returned error", "code": 403})

    monkeypatch.setattr(
        agent_v2_api, "build_retrieval_graph", lambda *_args, **_kwargs: _BrokenGraph()
    )
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "What is BERT?"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    errs = [e for e in events if e.get("type") == "error"]
    assert len(errs) == 1
    assert "403" in errs[0]["detail"]
    assert "Upstream LLM" in errs[0]["detail"]
    assert errs[0].get("provider_code") == 403


def test_v2_deferred_topic_shortcuts_sync_without_agent(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    def _fail_build_agent(**_kwargs):
        raise AssertionError("deferred topic should not build the agent")

    monkeypatch.setattr(agent_v2_api, "build_agent", _fail_build_agent)
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        resp = client.post(
            "/v2/agent/query",
            json={
                "question": "Найди противоречия между статьями по теме, которую я сформулирую следующим сообщением."
            },
            headers={"Accept": "application/json"},
        )
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["answer"].startswith("Хорошо. Пришлите тему")
    assert data["tool_trace"] == []
    assert data["run_metadata"]["shortcut"] == "deferred_topic_clarification"


def test_v2_deferred_topic_shortcuts_sse_without_graph(monkeypatch) -> None:
    from science_graphrag.api import agent_v2 as agent_v2_api

    def _fail_build_graph(*_args, **_kwargs):
        raise AssertionError("deferred topic should not build retrieval graph")

    monkeypatch.setattr(agent_v2_api, "build_retrieval_graph", _fail_build_graph)
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        with client.stream(
            "POST",
            "/v2/agent/query",
            json={
                "question": "Найди противоречия между статьями по теме, которую я сформулирую следующим сообщением."
            },
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    finals = [e for e in events if e.get("type") == "final_answer"]
    assert len(finals) == 1
    assert finals[0]["answer"].startswith("Хорошо. Пришлите тему")
    assert finals[0]["tool_trace"] == []
    assert finals[0]["run_metadata"]["shortcut"] == "deferred_topic_clarification"


def test_v1_has_deprecation_header(monkeypatch) -> None:
    from science_graphrag.api import agent as agent_api

    class _FakeOut:
        answer = "ok"
        citations = []
        tool_trace = []

    class _FakeAgent:
        def run(self, **_kwargs):
            return _FakeOut()

    monkeypatch.setattr(agent_api, "build_agent", lambda **_kwargs: _FakeAgent())
    test_app = _build_test_app()
    client = TestClient(test_app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        resp = client.post("/v1/agent/query", json={"question": "test"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    assert resp.headers.get("Deprecation") == "true"
    assert resp.headers.get("Sunset") == "2026-07-01"
    assert resp.headers.get("Link") == '</v2/agent/query>; rel="successor-version"'
