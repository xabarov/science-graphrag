"""Neo4j integration: removal orchestration must not break CITES when purge is blocked."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from neo4j import GraphDatabase

from science_graphrag.api.deps import build_store_registry_for_tests
from science_graphrag.api.workspace_work_removal import remove_work_from_workspace_result
from science_graphrag.config import get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _neo4j_available() -> bool:
    settings = get_settings()
    try:
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        neo.ensure_schema()
        neo.close()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.integration
def test_remove_from_workspace_purge_blocked_keeps_incoming_cites_edge() -> None:
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-rmws-{uuid.uuid4().hex[:16]}"
    w1 = f"it-rmw-{uuid.uuid4().hex[:12]}-a"
    w2 = f"it-rmw-{uuid.uuid4().hex[:12]}-b"

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    neo_store: Neo4jGraphStore | None = None
    try:
        with driver.session() as session:
            session.run(
                """
                CREATE (ws:Workspace {id: $ws_id, name: 'rm-test', created_at: '2020-01-01T00:00:00Z'})
                CREATE (w1:Work {id: $w1, title: 'Cited', publication_year: 2020})
                CREATE (w2:Work {id: $w2, title: 'Citing', publication_year: 2021})
                CREATE (ws)-[:CONTAINS]->(w1)
                CREATE (ws)-[:CONTAINS]->(w2)
                CREATE (w2)-[:CITES]->(w1)
                """,
                ws_id=ws_id,
                w1=w1,
                w2=w2,
            )

        neo_store = Neo4jGraphStore(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
        stores = build_store_registry_for_tests(
            neo4j=neo_store,
            qdrant_chunks=MagicMock(),
            qdrant_works=MagicMock(),
            qdrant_claims=MagicMock(),
            blob=MagicMock(),
        )
        out = remove_work_from_workspace_result(
            stores,
            settings=settings,
            workspace_id=ws_id,
            work_id=w1,
        )
        assert out["removal_status"] == "purge_blocked_by_incoming_cites"
        assert w1 not in (out["workspace"].get("work_ids") or [])

        with driver.session() as session:
            n = session.run(
                "MATCH (:Work {id: $w2})-[:CITES]->(:Work {id: $w1}) RETURN count(*) AS c",
                w1=w1,
                w2=w2,
            ).single()["c"]
            assert int(n) == 1
            ex = session.run("MATCH (w:Work {id: $id}) RETURN count(w) AS c", id=w1).single()["c"]
            assert int(ex) == 1
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w1, w2],
            )
        driver.close()
