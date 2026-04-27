"""API tests for workspace contradiction-detail endpoint."""

from __future__ import annotations

from typing import Any

import importlib
from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api.deps import get_stores

router_mod = importlib.import_module("science_graphrag.api.workspace_graph.router")


def _client() -> TestClient:
    api_main.app.dependency_overrides[get_stores] = lambda: type("S", (), {"neo4j": object()})()
    return TestClient(api_main.app)


def test_contradiction_detail_ok(monkeypatch: Any) -> None:
    def _fake_fetch(
        *_a: Any,
        **_kw: Any,
    ) -> dict[str, Any]:
        return {
            "workspace_id": "ws-1",
            "work_id_lo": "a",
            "work_id_hi": "b",
            "relationship": {
                "subtype": "scaling",
                "severity": "nuanced",
                "quote_a": "quote a " * 3,
                "quote_b": "quote b " * 3,
                "has_evidence": True,
                "underspecified": False,
            },
            "article_contradiction": None,
        }

    monkeypatch.setattr(router_mod, "fetch_workspace_contradiction_detail", _fake_fetch)
    client = _client()
    res = client.get(
        "/v1/workspaces/ws-1/graph/contradiction-detail",
        params={"work_id_a": "a", "work_id_b": "b"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["workspace_id"] == "ws-1"
    assert body["relationship"]["subtype"] == "scaling"


def test_contradiction_detail_404(monkeypatch: Any) -> None:
    monkeypatch.setattr(router_mod, "fetch_workspace_contradiction_detail", lambda *_a, **_k: None)
    client = _client()
    res = client.get(
        "/v1/workspaces/missing/graph/contradiction-detail",
        params={"work_id_a": "x", "work_id_b": "y"},
    )
    assert res.status_code == 404
    assert res.json().get("detail") == "contradiction_not_found"


def test_contradiction_detail_invalid_pair() -> None:
    client = _client()
    res = client.get(
        "/v1/workspaces/ws-1/graph/contradiction-detail",
        params={"work_id_a": "same", "work_id_b": "same"},
    )
    assert res.status_code == 400
