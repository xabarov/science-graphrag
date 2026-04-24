"""API tests for workspace graph v2 (mocked Neo4j projection)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api import workspaces as workspaces_mod
from science_graphrag.api import workspace_graph as wg_mod


def _client() -> TestClient:
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

    monkeypatch.setattr(workspaces_mod, "project_workspace_graph", _fake_project)
    client = _client()
    res = client.get("/v1/workspaces/ws-x/graph?mode=inner_only&depth=1&include_external=false")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["graph_scope"] == "workspace_v2"
    assert body["nodes"][0]["workspace_membership"] == "internal"


def test_get_workspace_graph_stats_smoke(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        workspaces_mod,
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
    from science_graphrag.api.workspace_graph import _annotate_membership_and_cites

    nodes = [
        {"id": "a", "type": "Work"},
        {"id": "b", "type": "Work"},
        {"id": "x", "type": "Author"},
    ]
    edges = [
        {"id": "e1", "source": "a", "target": "b", "type": "CITES"},
        {"id": "e2", "source": "a", "target": "x", "type": "OF_AUTHOR"},
    ]
    inc, exc = _annotate_membership_and_cites(nodes, edges, {"a"})
    assert inc == 2
    assert exc == 1
    assert nodes[0]["workspace_membership"] == "internal"
    assert nodes[1]["workspace_membership"] == "external"
