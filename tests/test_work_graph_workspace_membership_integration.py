"""Neo4j-backed tests: work graph optional ``workspace_id`` membership (Phase 2)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from neo4j import GraphDatabase

from science_graphrag.api.works.graph_neighborhood import (
    load_work_graph_workspace_internal_ids,
    work_graph_neighborhood,
)
from science_graphrag.config import get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from tests.fixtures.work_graph_workspace_authorship_parity import (
    work_graph_workspace_membership_by_work_id,
)


class _StoresStub:  # pylint: disable=too-few-public-methods
    """Minimal registry for ``work_graph_neighborhood`` (matches authorship integration tests)."""

    def __init__(self, neo4j: Neo4jGraphStore) -> None:
        self.neo4j = neo4j


def _neo4j_available() -> bool:
    settings = get_settings()
    try:
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        neo.ensure_schema()
        neo.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _seed_workspace_internal_cites_external(driver: Any, ws_id: str, w_in: str, w_out: str) -> None:
    """Internal work cites an external work (not in CONTAINS)."""
    with driver.session() as session:
        session.run(
            """
            CREATE (ws:Workspace {
              id: $ws_id, name: 'it-ws-mem', created_at: '2020-01-01T00:00:00Z'})
            CREATE (wi:Work {id: $w_in, title: 'Internal cites', publication_year: 2024})
            CREATE (we:Work {id: $w_out, title: 'External cited', publication_year: 2023})
            CREATE (ws)-[:CONTAINS]->(wi)
            CREATE (wi)-[:CITES]->(we)
            """,
            ws_id=ws_id,
            w_in=w_in,
            w_out=w_out,
        )


def _delete_nodes(driver: Any, *, ws_id: str, work_ids: list[str]) -> None:
    with driver.session() as session:
        for wid in work_ids:
            session.run("MATCH (w:Work {id: $id}) DETACH DELETE w", id=wid)
        session.run("MATCH (ws:Workspace {id: $id}) DETACH DELETE ws", id=ws_id)


@pytest.mark.skipif(not _neo4j_available(), reason="Neo4j not reachable")
def test_work_graph_with_workspace_context_sets_membership() -> None:
    settings = get_settings()
    suffix = uuid.uuid4().hex[:10]
    ws_id = f"ws-mem-{suffix}"
    w_in = f"w-in-{suffix}"
    w_out = f"w-out-{suffix}"
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        _seed_workspace_internal_cites_external(driver, ws_id, w_in, w_out)
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            with neo.session() as session:
                iws, err = load_work_graph_workspace_internal_ids(
                    session, workspace_id=ws_id, center_work_id=w_in
                )
                assert err is None
                assert w_in in iws
                assert w_out not in iws

            payload = work_graph_neighborhood(
                _StoresStub(neo),
                w_in,
                neighbor_limit=200,
                depth=1,
                prioritize="Work,Method,Dataset",
                view="reader",
                workspace_id=ws_id,
                workspace_internal_work_ids=iws,
            )
            assert payload is not None
            assert payload["meta"].get("graph_mode") == "work_workspace_context"
            assert payload["meta"].get("workspace_id") == ws_id
            mem = work_graph_workspace_membership_by_work_id(payload)
            assert mem.get(w_in) == "internal"
            assert mem.get(w_out) == "external"

            bare = work_graph_neighborhood(
                _StoresStub(neo),
                w_in,
                neighbor_limit=200,
                depth=1,
                prioritize="Work,Method,Dataset",
                view="reader",
            )
            assert bare is not None
            assert bare["meta"].get("graph_mode") == "work_capped"
            assert bare["meta"].get("workspace_id") is None
            for n in bare.get("nodes") or []:
                if str(n.get("type") or "") == "Work":
                    assert not str(n.get("workspace_membership") or "").strip()
        finally:
            neo.close()
    finally:
        _delete_nodes(driver, ws_id=ws_id, work_ids=[w_in, w_out])
        driver.close()


@pytest.mark.skipif(not _neo4j_available(), reason="Neo4j not reachable")
def test_load_work_graph_workspace_internal_ids_errors() -> None:
    settings = get_settings()
    suffix = uuid.uuid4().hex[:10]
    ws_id = f"ws-mem2-{suffix}"
    w_in = f"w-in2-{suffix}"
    w_other = f"w-other-{suffix}"
    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    try:
        with driver.session() as session:
            session.run(
                """
                CREATE (ws:Workspace {
                  id: $ws_id, name: 'it-ws2', created_at: '2020-01-01T00:00:00Z'})
                CREATE (wi:Work {id: $w_in, title: 'Only internal', publication_year: 2024})
                CREATE (wo:Work {id: $w_other, title: 'Orphan', publication_year: 2023})
                CREATE (ws)-[:CONTAINS]->(wi)
                """,
                ws_id=ws_id,
                w_in=w_in,
                w_other=w_other,
            )
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        try:
            with neo.session() as session:
                missing_ws, err1 = load_work_graph_workspace_internal_ids(
                    session, workspace_id="no-such-workspace-999", center_work_id=w_in
                )
                assert missing_ws is None and err1 == "workspace_not_found"
                not_member, err2 = load_work_graph_workspace_internal_ids(
                    session, workspace_id=ws_id, center_work_id=w_other
                )
                assert not_member is None and err2 == "work_not_in_workspace"
        finally:
            neo.close()
    finally:
        _delete_nodes(driver, ws_id=ws_id, work_ids=[w_in, w_other])
        driver.close()
