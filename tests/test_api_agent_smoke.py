from __future__ import annotations

from fastapi.testclient import TestClient

from science_graphrag.api.main import app
from science_graphrag.config import Settings


def test_post_agent_query_disabled_by_default() -> None:
    client = TestClient(app)
    res = client.post("/v1/agent/query", json={"question": "hello"})
    assert res.status_code == 503
    assert res.json().get("detail") == "agent_disabled"


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
    monkeypatch.setattr(
        agent_api,
        "get_settings",
        lambda: Settings(agent_enabled=True),
    )
    client = TestClient(app)
    # Override dependency used by FastAPI router.
    client.app.dependency_overrides[agent_api.get_settings] = lambda: Settings(agent_enabled=True)
    try:
        res = client.post("/v1/agent/query", json={"question": "hello"})
    finally:
        client.app.dependency_overrides.pop(agent_api.get_settings, None)
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "ok"
    assert body["tool_trace"][0]["tool"] == "final_answer"
