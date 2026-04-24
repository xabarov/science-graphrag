"""Neo4j-backed checks for workspace graph projection (Wave J)."""

from __future__ import annotations

import uuid

import pytest
from neo4j import GraphDatabase

from science_graphrag.api.workspace_graph import (
    project_workspace_graph,
    workspace_graph_neighbors,
    workspace_graph_stats,
)
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
def test_workspace_graph_inner_only_two_works_cites_and_full_ignores_type_filter() -> None:
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-{uuid.uuid4().hex[:16]}"
    w1 = f"it-w-{uuid.uuid4().hex[:12]}-a"
    w2 = f"it-w-{uuid.uuid4().hex[:12]}-b"
    mid = f"it-m-{uuid.uuid4().hex[:12]}"

    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        with driver.session() as session:
            session.run(
                """
                CREATE (ws:Workspace {id: $ws_id, name: $ws_name, created_at: '2020-01-01T00:00:00Z'})
                CREATE (w1:Work {id: $w1, title: 'Paper A', publication_year: 2020})
                CREATE (w2:Work {id: $w2, title: 'Paper B', publication_year: 2021})
                CREATE (m:Method {id: $mid, name: 'ResNet'})
                CREATE (ws)-[:CONTAINS]->(w1)
                CREATE (ws)-[:CONTAINS]->(w2)
                CREATE (w1)-[:CITES]->(w2)
                CREATE (w1)-[:USES_METHOD]->(m)
                """,
                ws_id=ws_id,
                ws_name="integration-ws-graph",
                w1=w1,
                w2=w2,
                mid=mid,
            )

        stats = workspace_graph_stats(settings, ws_id)
        assert stats is not None
        assert int(stats["internal_citations"]) >= 1

        g = project_workspace_graph(
            settings,
            ws_id,
            mode="inner_only",
            depth=1,
            include_external=False,
            node_types=None,
        )
        assert g is not None
        by_id = {n["id"]: n for n in g.get("nodes") or []}
        assert w1 in by_id and w2 in by_id
        assert by_id[w1].get("workspace_membership") == "internal"
        assert by_id[w2].get("workspace_membership") == "internal"
        cites = [
            e
            for e in (g.get("edges") or [])
            if str(e.get("type") or "") == "CITES" and str(e.get("source") or "") == w1 and str(e.get("target") or "") == w2
        ]
        assert len(cites) >= 1

        g_work_only = project_workspace_graph(
            settings,
            ws_id,
            mode="inner_only",
            depth=1,
            include_external=False,
            node_types="Work",
        )
        assert g_work_only is not None
        assert not any(str(n.get("type") or "") == "Method" for n in (g_work_only.get("nodes") or []))

        g_full = project_workspace_graph(
            settings,
            ws_id,
            mode="full",
            depth=1,
            include_external=False,
            node_types="Work",
        )
        assert g_full is not None
        assert any(str(n.get("id") or "") == mid for n in (g_full.get("nodes") or []))

        nb = workspace_graph_neighbors(settings, ws_id, w1, depth=2, limit=50)
        assert nb is not None
        assert int(nb["depth_requested"]) == 2
        assert int(nb["depth_effective"]) == 2
    finally:
        with driver.session() as session:
            session.run(
                """
                MATCH (n)
                WHERE n.id IN $ids
                DETACH DELETE n
                """,
                ids=[ws_id, w1, w2, mid],
            )
        driver.close()
