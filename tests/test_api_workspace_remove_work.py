"""HTTP tests for DELETE /v1/workspaces/{id}/works/{work_id}."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from science_graphrag.api.deps import get_stores
from science_graphrag.api.workspaces import router as workspaces_router
from science_graphrag.config import Settings, get_settings


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(workspaces_router, prefix="/v1")
    return app


def test_delete_workspace_work_returns_removal_payload() -> None:
    neo = MagicMock()
    neo.workspace_get.side_effect = [
        {"id": "ws1", "name": "A", "work_ids": ["w1"], "unbounded": False},
        {"id": "ws1", "name": "A", "work_ids": [], "unbounded": False},
    ]
    neo.workspace_remove_work.return_value = True
    neo.count_work_workspace_memberships.return_value = 1
    neo.work_has_incoming_cites.return_value = False
    stores = MagicMock()
    stores.neo4j = neo
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    stores.qdrant_claims = MagicMock()
    stores.blob = MagicMock()

    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: stores
    try:
        resp = client.delete("/v1/workspaces/ws1/works/w1")
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["removal_status"] == "detached_only"
    assert data["workspace"]["id"] == "ws1"


def test_delete_workspace_work_400_when_not_member() -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = {
        "id": "ws1",
        "name": "A",
        "work_ids": ["w2"],
        "unbounded": False,
    }
    stores = MagicMock()
    stores.neo4j = neo
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()
    stores.qdrant_claims = MagicMock()
    stores.blob = MagicMock()

    client = TestClient(_app())
    client.app.dependency_overrides[get_settings] = lambda: Settings()
    client.app.dependency_overrides[get_stores] = lambda: stores
    try:
        resp = client.delete("/v1/workspaces/ws1/works/w1")
    finally:
        client.app.dependency_overrides.pop(get_settings, None)
        client.app.dependency_overrides.pop(get_stores, None)

    assert resp.status_code == 400
    assert resp.json().get("detail") == "work_not_in_workspace"
