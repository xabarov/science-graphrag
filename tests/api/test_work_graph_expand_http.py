"""HTTP smoke for ``GET /v1/works/{work_id}/graph/expand`` (Phase 2 tail)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.api.deps import get_stores as app_get_stores
from science_graphrag.api.works import router as works_router


def test_work_graph_expand_http_returns_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expand endpoint returns JSON with ``meta.expanded_aggregator_id``."""

    wid = "http-expand-work-1"
    agg = f"agg:{wid.replace(':', '%3A')}:author:AUTHORED"

    def _fake_expand(
        _stores: Any,
        work_id: str,
        aggregator_id: str,
        *,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        assert work_id == wid
        assert aggregator_id == agg
        assert limit == 10
        return {
            "nodes": [{"id": wid, "type": "Work", "node_kind": "Work"}],
            "edges": [],
            "meta": {"expanded_aggregator_id": aggregator_id},
        }

    monkeypatch.setattr(works_router, "expand_work_aggregator", _fake_expand)

    client = TestClient(api_main.app)
    client.app.dependency_overrides[app_get_stores] = lambda: SimpleNamespace(neo4j=object())
    try:
        res = client.get(
            "/v1/works/http-expand-work-1/graph/expand",
            params={"aggregator_id": agg, "limit": 10},
        )
    finally:
        client.app.dependency_overrides.pop(app_get_stores, None)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["meta"]["expanded_aggregator_id"] == agg
    assert body["nodes"]
