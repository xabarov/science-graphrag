"""Integration-style API tests for dedup conflict list/decide behavior."""

from __future__ import annotations

from fastapi.testclient import TestClient

from science_graphrag.api import main as api_main
from science_graphrag.config import Settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import AuthorDedupConflict, EntityDedupConflict


class _FakeNeo4j:
    def workspace_get(self, workspace_id: str):
        return {"id": workspace_id}

    def fetch_author_display_name(self, author_id: str) -> str:
        return {"a-1": "Alice", "a-2": "Alicia", "a-3": "Bob", "a-4": "Bobby"}.get(
            author_id, author_id
        )

    def fetch_entity_display_label(self, entity_type: str, entity_id: str) -> str:
        _ = entity_type
        return {"i-1": "Org One", "i-2": "Org Uno", "i-3": "Other Org", "i-4": "Else Org"}.get(
            entity_id, entity_id
        )

    def merge_institution_into_canonical(self, keep_id: str, drop_id: str) -> bool:
        _ = (keep_id, drop_id)
        return True


def _mk_client(settings: Settings) -> TestClient:
    client = TestClient(api_main.app)
    fake_stores = type(
        "_FakeStores",
        (),
        {
            "neo4j": _FakeNeo4j(),
            "qdrant_chunks": object(),
            "qdrant_works": object(),
        },
    )()
    client.app.dependency_overrides[api_main.get_settings] = lambda: settings
    client.app.dependency_overrides[api_main.get_stores] = lambda: fake_stores
    return client


def test_author_conflicts_filter_origin_and_include_display_names(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'dedup_api_authors.db'}"
    settings = Settings(database_url=db_url)
    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = session_factory(engine)

    with factory() as session:
        session.add(
            AuthorDedupConflict(
                workspace_id="ws-1",
                author_id_a="a-1",
                author_id_b="a-2",
                similarity_score=0.91,
                status="pending",
                fingerprint="fp-a-ingest",
                origin="ingest",
            )
        )
        session.add(
            AuthorDedupConflict(
                workspace_id="ws-1",
                author_id_a="a-3",
                author_id_b="a-4",
                similarity_score=0.89,
                status="pending",
                fingerprint="fp-a-scan",
                origin="scan",
            )
        )
        session.commit()

    client = _mk_client(settings)
    try:
        res = client.get("/v1/workspaces/ws-1/dedup/authors/conflicts?status=pending&origin=ingest")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        row = body["items"][0]
        assert row["origin"] == "ingest"
        assert row["author_name_a"] == "Alice"
        assert row["author_name_b"] == "Alicia"
    finally:
        client.app.dependency_overrides.clear()


def test_entity_conflicts_filter_workspace_origin_and_decide_guard(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'dedup_api_entities.db'}"
    settings = Settings(database_url=db_url)
    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = session_factory(engine)

    with factory() as session:
        session.add(
            EntityDedupConflict(
                entity_type="institution",
                entity_id_a="i-1",
                entity_id_b="i-2",
                similarity_score=0.9,
                status="pending",
                fingerprint="fp-e-ws1",
                workspace_id="ws-1",
                origin="ingest",
            )
        )
        session.add(
            EntityDedupConflict(
                entity_type="institution",
                entity_id_a="i-3",
                entity_id_b="i-4",
                similarity_score=0.9,
                status="pending",
                fingerprint="fp-e-ws2",
                workspace_id="ws-2",
                origin="ingest",
            )
        )
        session.commit()

    client = _mk_client(settings)
    try:
        list_res = client.get(
            "/v1/dedup/entity?entity_type=institution&status=pending&workspace_id=ws-1&origin=ingest"
        )
        assert list_res.status_code == 200
        list_body = list_res.json()
        assert list_body["total"] == 1
        row = list_body["items"][0]
        assert row["workspace_id"] == "ws-1"
        assert row["origin"] == "ingest"
        assert row["entity_label_a"] == "Org One"
        assert row["entity_label_b"] == "Org Uno"

        conflict_ws2 = None
        with factory() as session:
            conflict_ws2 = session.query(EntityDedupConflict).filter_by(workspace_id="ws-2").first()
        assert conflict_ws2 is not None
        decide_res = client.post(
            f"/v1/dedup/entity/{conflict_ws2.id}/decide?workspace_id=ws-1",
            json={"decision": "skip"},
        )
        assert decide_res.status_code == 400
        assert decide_res.json()["detail"] == "workspace_mismatch"
    finally:
        client.app.dependency_overrides.clear()
