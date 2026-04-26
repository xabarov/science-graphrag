from __future__ import annotations

from fastapi.testclient import TestClient

from science_graphrag.api.deps import get_stores
from science_graphrag.api.main import app
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


def test_post_agent_query_enabled_smoke(monkeypatch) -> None:
    from science_graphrag.api import agent as agent_api

    class _FakeOut:
        answer = "ok"
        citations = [{"work_id": "w1"}]
        tool_trace = [{"step": 1, "tool": "final_answer"}]

    class _FakeAgent:
        def run(self, **_kwargs):
            return _FakeOut()

    monkeypatch.setattr(agent_api, "build_agent", lambda **_kwargs: _FakeAgent())
    client = TestClient(app)
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: _EMPTY_STORES
    try:
        res = client.post("/v1/agent/query", json={"question": "hello"})
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "ok"
    assert body["tool_trace"][0]["tool"] == "final_answer"
