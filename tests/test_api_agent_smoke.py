from __future__ import annotations

from fastapi.testclient import TestClient

from science_graphrag.api.main import app


def test_post_agent_query_returns_gone() -> None:
    client = TestClient(app)
    res = client.post("/v1/agent/query", json={"question": "hello"})
    assert res.status_code == 410
    body = res.json()
    assert "replacement" in body
    assert body.get("replacement") == "/v2/agent/query"
    assert res.headers.get("Link") == '</v2/agent/query>; rel="successor-version"'
