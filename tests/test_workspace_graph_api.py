"""API tests for workspace graph v2 (mocked Neo4j projection)."""

from __future__ import annotations

import importlib
from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api.deps import get_stores
from science_graphrag.api.workspace_graph import router as graph_router
from science_graphrag.api.workspace_graph.router import (
    project_workspace_graph,
    workspace_graph_stats,
)

graph_router_module = importlib.import_module("science_graphrag.api.workspace_graph.router")


def _client() -> TestClient:
    api_main.app.dependency_overrides[get_stores] = lambda: type("S", (), {"neo4j": object()})()
    return TestClient(api_main.app)


def test_get_workspace_graph_v2_smoke(monkeypatch: Any) -> None:
    def _fake_project(*_a: Any, **_kw: Any) -> dict[str, Any]:
        return {
            "work_id": "",
            "nodes": [
                {
                    "id": "w1",
                    "type": "Work",
                    "label": "A",
                    "workspace_membership": "internal",
                    "internal_cite_count": 0,
                    "external_cite_count": 0,
                },
            ],
            "edges": [],
            "meta": {
                "graph_scope": "workspace_v2",
                "mode": _kw.get("mode", "inner_only"),
                "graph_depth_effective": 1,
                "gds_used": False,
                "gds_runtime_available": False,
            },
        }

    monkeypatch.setattr(graph_router_module, "project_workspace_graph", _fake_project)
    client = _client()
    res = client.get("/v1/workspaces/ws-x/graph?mode=inner_only&depth=1&include_external=false")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["graph_scope"] == "workspace_v2"
    assert body["nodes"][0]["workspace_membership"] == "internal"


def test_get_workspace_graph_passes_include_claims(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_project(*_a: Any, **_kw: Any) -> dict[str, Any]:
        captured.update(_kw)
        return {"work_id": "", "nodes": [], "edges": [], "meta": {"graph_scope": "workspace_v2"}}

    monkeypatch.setattr(graph_router_module, "project_workspace_graph", _fake_project)
    client = _client()
    res = client.get("/v1/workspaces/ws-x/graph?include_claims=true&claims_per_work=8&claims_max_total=40")
    assert res.status_code == 200
    assert captured.get("include_claims") is True
    assert captured.get("claims_per_work") == 8
    assert captured.get("claims_max_total") == 40


def test_get_workspace_graph_passes_prioritize(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    def _fake_project(*_a: Any, **_kw: Any) -> dict[str, Any]:
        captured.update(_kw)
        return {"work_id": "", "nodes": [], "edges": [], "meta": {"graph_scope": "workspace_v2"}}

    monkeypatch.setattr(graph_router_module, "project_workspace_graph", _fake_project)
    client = _client()
    res = client.get("/v1/workspaces/ws-x/graph?prioritize=Method,Dataset")
    assert res.status_code == 200
    assert captured["prioritize"] == "Method,Dataset"


def test_get_workspace_graph_stats_smoke(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        graph_router_module,
        "workspace_graph_stats",
        lambda *_a, **_k: {
            "workspace_id": "ws-x",
            "works_count": 2,
            "authors_count": 5,
            "internal_citations": 1,
            "external_citations": 3,
            "external_works_count": 2,
        },
    )
    client = _client()
    res = client.get("/v1/workspaces/ws-x/graph/stats")
    assert res.status_code == 200
    assert res.json()["works_count"] == 2
    assert res.json()["external_citations"] == 3


def test_workspace_graph_annotate_membership() -> None:
    from science_graphrag.api.workspace_graph.projection import annotate_membership_and_cites

    nodes = [
        {"id": "a", "type": "Work"},
        {"id": "b", "type": "Work"},
        {"id": "x", "type": "Author"},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b", "type": "CITES"},
        {"id": "e2", "source": "a", "target": "x", "type": "OF_AUTHOR"},
    ]
    inc, exc = annotate_membership_and_cites(nodes, edges, {"a"})
    assert inc == 2
    assert exc == 1
    assert nodes[0]["workspace_membership"] == "internal"
    assert nodes[1]["workspace_membership"] == "external"


def test_workspace_graph_imports() -> None:
    assert graph_router is not None
    assert project_workspace_graph is not None


def test_workspace_graph_shim() -> None:
    from science_graphrag.api.workspace_graph import router as shim_router

    assert workspace_graph_stats is not None
    assert shim_router is graph_router
