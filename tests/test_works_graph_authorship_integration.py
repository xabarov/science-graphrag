"""Phase 0 Neo4j-backed parity tests: work graph vs workspace graph for authors.

Reader-view integration tests assert Neo4j-backed parity after Phase 1 collapse.
The raw-view test stays green.

See ``docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md``.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from neo4j import GraphDatabase

from science_graphrag.api.works.graph_neighborhood import (
    _aggregator_id,
    expand_work_aggregator,
    work_graph_neighborhood,
)
from science_graphrag.api.workspace_graph.cypher import (
    project_workspace_graph,
    workspace_graph_stats,
)
from science_graphrag.config import get_settings
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from tests.fixtures.work_graph_workspace_authorship_parity import (
    logical_author_slots_workspace_payload,
    surfaced_author_count_reader_work_graph,
    workspace_one_hop_subgraph,
)


def _neo4j_available() -> bool:
    settings = get_settings()
    try:
        neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
        neo.ensure_schema()
        neo.close()
        return True
    except Exception:  # noqa: BLE001
        return False


def _seed_work_with_two_authors(
    driver: Any, ws_id: str, w_id: str, *, author_ids: tuple[str, str]
) -> tuple[str, str, str]:
    """Create Workspace + Work + 2 Authorship + 2 Author + optional Institution affiliation."""
    ash1 = f"{w_id}:ash:1"
    ash2 = f"{w_id}:ash:2"
    inst1 = f"it-i-{uuid.uuid4().hex[:12]}"
    a1, a2 = author_ids
    with driver.session() as session:
        session.run(
            """
            CREATE (ws:Workspace {id: $ws_id, name: 'it-ws', created_at: '2020-01-01T00:00:00Z'})
            CREATE (w:Work {id: $w_id, title: 'Parity Paper', publication_year: 2024})
            CREATE (a1:Author {id: $a1, full_name: 'Wei Liu'})
            CREATE (a2:Author {id: $a2, full_name: 'Jia Deng'})
            CREATE (inst:Institution {id: $inst1, name: 'IBM Research'})
            CREATE (ash1:Authorship {id: $ash1, author_position: 1, raw_affiliation: 'IBM'})
            CREATE (ash2:Authorship {id: $ash2, author_position: 2})
            CREATE (ws)-[:CONTAINS]->(w)
            CREATE (w)-[:HAS_AUTHORSHIP]->(ash1)-[:OF_AUTHOR]->(a1)
            CREATE (w)-[:HAS_AUTHORSHIP]->(ash2)-[:OF_AUTHOR]->(a2)
            CREATE (ash1)-[:AFFILIATED_WITH]->(inst)
            """,
            ws_id=ws_id,
            w_id=w_id,
            a1=a1,
            a2=a2,
            inst1=inst1,
            ash1=ash1,
            ash2=ash2,
        )
    return ash1, ash2, inst1


def _seed_work_two_authorships_without_of_author(
    driver: Any, ws_id: str, w_id: str
) -> tuple[str, str]:
    """Workspace + Work + two Authorship rows; no OF_AUTHOR (synthetic authors on work graph)."""
    ash1 = f"{w_id}:ash:1"
    ash2 = f"{w_id}:ash:2"
    with driver.session() as session:
        session.run(
            """
            CREATE (ws:Workspace {id: $ws_id, name: 'it-ws', created_at: '2020-01-01T00:00:00Z'})
            CREATE (w:Work {id: $w_id, title: 'No OF Author', publication_year: 2023})
            CREATE (ash1:Authorship {id: $ash1, author_position: 1, raw_affiliation: 'Lab A'})
            CREATE (ash2:Authorship {id: $ash2, author_position: 2, raw_affiliation: 'Lab B'})
            CREATE (ws)-[:CONTAINS]->(w)
            CREATE (w)-[:HAS_AUTHORSHIP]->(ash1)
            CREATE (w)-[:HAS_AUTHORSHIP]->(ash2)
            """,
            ws_id=ws_id,
            w_id=w_id,
            ash1=ash1,
            ash2=ash2,
        )
    return ash1, ash2


def _seed_work_with_five_authors(driver: Any, ws_id: str, w_id: str) -> list[str]:
    """Five Authorship + Author + OF_AUTHOR for aggregation tests."""
    author_ids = [f"{w_id}-auth-{i}" for i in range(1, 6)]
    ash_ids = [f"{w_id}:ash:{i}" for i in range(1, 6)]
    with driver.session() as session:
        session.run(
            """
            CREATE (ws:Workspace {id: $ws_id, name: 'it-ws', created_at: '2020-01-01T00:00:00Z'})
            CREATE (w:Work {id: $w_id, title: 'Many Authors', publication_year: 2022})
            CREATE (ws)-[:CONTAINS]->(w)
            """,
            ws_id=ws_id,
            w_id=w_id,
        )
        for i, (aid, ash) in enumerate(zip(author_ids, ash_ids, strict=True), start=1):
            session.run(
                """
                MATCH (w:Work {id: $w_id})
                CREATE (a:Author {id: $aid, full_name: $fn})
                CREATE (ash:Authorship {id: $ash, author_position: $pos})
                CREATE (w)-[:HAS_AUTHORSHIP]->(ash)-[:OF_AUTHOR]->(a)
                """,
                w_id=w_id,
                aid=aid,
                ash=ash,
                pos=i,
                fn=f"Author {i}",
            )
    return author_ids


class _StoresStub:  # pylint: disable=too-few-public-methods
    """Minimal registry for ``work_graph_neighborhood`` integration calls."""

    def __init__(self, neo4j: Neo4jGraphStore) -> None:
        self.neo4j = neo4j


@pytest.mark.integration
def test_work_graph_reader_surfaces_authors_when_neo4j_has_them() -> None:
    """Reader work graph surfaces authors when Neo4j has HAS_AUTHORSHIP/OF_AUTHOR."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-{uuid.uuid4().hex[:16]}"
    w_id = f"it-w-{uuid.uuid4().hex[:12]}"
    a1 = f"it-a-{uuid.uuid4().hex[:12]}-1"
    a2 = f"it-a-{uuid.uuid4().hex[:12]}-2"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = inst1 = ""
    try:
        ash1, ash2, inst1 = _seed_work_with_two_authors(driver, ws_id, w_id, author_ids=(a1, a2))
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        payload = work_graph_neighborhood(
            _StoresStub(neo_store),
            w_id,
            neighbor_limit=200,
            depth=1,
            view="reader",
        )
        assert payload is not None
        surfaced = surfaced_author_count_reader_work_graph(payload, w_id)
        assert surfaced >= 2, (
            f"Expected at least 2 surfaced authors for seeded work, got {surfaced}. "
            f"Nodes types: {[n.get('type') for n in payload['nodes']]}; "
            f"edge types: {[e.get('type') for e in payload['edges']]}"
        )
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, a1, a2, ash1, ash2, inst1],
            )
        driver.close()


@pytest.mark.integration
def test_work_and_workspace_graphs_agree_on_author_count_for_same_work() -> None:
    """Workspace stats and reader work graph agree on author count for one Work."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-{uuid.uuid4().hex[:16]}"
    w_id = f"it-w-{uuid.uuid4().hex[:12]}"
    a1 = f"it-a-{uuid.uuid4().hex[:12]}-1"
    a2 = f"it-a-{uuid.uuid4().hex[:12]}-2"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = inst1 = ""
    try:
        ash1, ash2, inst1 = _seed_work_with_two_authors(driver, ws_id, w_id, author_ids=(a1, a2))
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        ws_stats = workspace_graph_stats(neo_store, ws_id)
        assert ws_stats is not None
        ws_authors = int(ws_stats.get("authors_count") or 0)

        work_payload = work_graph_neighborhood(
            _StoresStub(neo_store), w_id, neighbor_limit=200, depth=1, view="reader"
        )
        assert work_payload is not None
        work_authors = surfaced_author_count_reader_work_graph(work_payload, w_id)

        assert work_authors == ws_authors, (
            f"Workspace graph reports {ws_authors} authors for the only work; "
            f"work graph (reader) surfaces {work_authors}. Two API surfaces must "
            f"agree on author count for the same Work."
        )
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, a1, a2, ash1, ash2, inst1],
            )
        driver.close()


@pytest.mark.integration
def test_work_graph_raw_view_includes_authorship_and_has_authorship_in_neo4j_seed() -> (
    None
):  # pylint: disable=too-many-locals
    """Locks the raw-view contract on a real Neo4j seed."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-{uuid.uuid4().hex[:16]}"
    w_id = f"it-w-{uuid.uuid4().hex[:12]}"
    a1 = f"it-a-{uuid.uuid4().hex[:12]}-1"
    a2 = f"it-a-{uuid.uuid4().hex[:12]}-2"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = inst1 = ""
    try:
        ash1, ash2, inst1 = _seed_work_with_two_authors(driver, ws_id, w_id, author_ids=(a1, a2))
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        payload = work_graph_neighborhood(
            _StoresStub(neo_store), w_id, neighbor_limit=200, depth=1, view="raw"
        )
        assert payload is not None
        ash_in_payload = [
            str(n.get("id") or "")
            for n in payload["nodes"]
            if str(n.get("type") or "") == "Authorship"
        ]
        assert {ash1, ash2}.issubset(
            set(ash_in_payload)
        ), f"Raw view must include both seeded Authorship nodes; got {ash_in_payload}"
        has_authorship_edges = [
            e
            for e in payload["edges"]
            if str(e.get("type") or "").upper() == "HAS_AUTHORSHIP"
            and str(e.get("source") or "") == w_id
        ]
        assert len(has_authorship_edges) >= 2, (
            f"Raw view must include 2 HAS_AUTHORSHIP edges from center, "
            f"got {len(has_authorship_edges)}"
        )
        authored_edges = [
            e for e in payload["edges"] if str(e.get("type") or "").upper() == "AUTHORED"
        ]
        assert (
            not authored_edges
        ), "Raw view must not synthesize AUTHORED edges; that is reader-view behavior."
        of_edges = [e for e in payload["edges"] if str(e.get("type") or "").upper() == "OF_AUTHOR"]
        assert len(of_edges) >= 2, (
            "Raw view should materialize OF_AUTHOR from Neo4j for each Authorship–Author link; "
            f"got {len(of_edges)} OF_AUTHOR edges"
        )
        author_nodes = [n for n in payload["nodes"] if str(n.get("type") or "") == "Author"]
        assert len(author_nodes) >= 2, (
            "Raw view should include Author nodes when OF_AUTHOR is materialized; "
            f"got {len(author_nodes)}"
        )
        for n in payload["nodes"]:
            if str(n.get("type") or "") != "Authorship":
                continue
            props = n.get("properties") or {}
            assert (
                "author_entity_id" not in props
            ), "Raw view must not expose reader-only author_entity_id on Authorship nodes"
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, a1, a2, ash1, ash2, inst1],
            )
        driver.close()


@pytest.mark.integration
def test_workspace_graph_slice_matches_work_reader_author_cardinality() -> None:
    """Phase 3: workspace 1-hop slice vs reader work graph (non-truncated work graph)."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-slice-{uuid.uuid4().hex[:12]}"
    w_id = f"it-w-slice-{uuid.uuid4().hex[:10]}"
    a1 = f"it-a-{uuid.uuid4().hex[:12]}-1"
    a2 = f"it-a-{uuid.uuid4().hex[:12]}-2"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = inst1 = ""
    try:
        ash1, ash2, inst1 = _seed_work_with_two_authors(driver, ws_id, w_id, author_ids=(a1, a2))
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        ws_payload = project_workspace_graph(
            neo_store, settings, ws_id, view="reader", mode="inner_only"
        )
        assert ws_payload is not None
        _wn, we = workspace_one_hop_subgraph(w_id, ws_payload["nodes"], ws_payload["edges"])
        ws_logical = logical_author_slots_workspace_payload(w_id, we)

        work_payload = work_graph_neighborhood(
            _StoresStub(neo_store), w_id, neighbor_limit=200, depth=1, view="reader"
        )
        assert work_payload is not None
        assert work_payload["meta"].get("is_truncated") is False
        wg = surfaced_author_count_reader_work_graph(work_payload, w_id)
        assert wg == ws_logical == 2, (wg, ws_logical)
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, a1, a2, ash1, ash2, inst1],
            )
        driver.close()


@pytest.mark.integration
def test_work_graph_without_of_author_matches_workspace_logical_slots() -> None:
    """Phase 3: no OF_AUTHOR; work reader uses va:; workspace slice counts authorship rows."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-noof-{uuid.uuid4().hex[:12]}"
    w_id = f"it-w-noof-{uuid.uuid4().hex[:10]}"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = ""
    try:
        ash1, ash2 = _seed_work_two_authorships_without_of_author(driver, ws_id, w_id)
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        ws_payload = project_workspace_graph(
            neo_store, settings, ws_id, view="reader", mode="inner_only"
        )
        assert ws_payload is not None
        _wn, we = workspace_one_hop_subgraph(w_id, ws_payload["nodes"], ws_payload["edges"])
        ws_logical = logical_author_slots_workspace_payload(w_id, we)

        work_payload = work_graph_neighborhood(
            _StoresStub(neo_store),
            w_id,
            neighbor_limit=200,
            depth=1,
            view="reader",
            include_authorship_debug=True,
        )
        assert work_payload is not None
        assert work_payload["meta"].get("authorship_projection") == "synthesized"
        assert ws_logical == 2
        va_ids = [
            str(n.get("id") or "")
            for n in work_payload["nodes"]
            if str(n.get("type") or "") == "Author" and str(n.get("id") or "").startswith("va:")
        ]
        assert len(va_ids) == 2
        assert surfaced_author_count_reader_work_graph(work_payload, w_id) == 2
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, ash1, ash2],
            )
        driver.close()


@pytest.mark.integration
def test_work_graph_truncation_preserves_center_authors_count() -> None:
    """Phase 3: truncation may drop neighbors; center authors_count stays Neo4j-true."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-trunc-{uuid.uuid4().hex[:12]}"
    w_id = f"it-w-trunc-{uuid.uuid4().hex[:10]}"
    a1 = f"it-a-{uuid.uuid4().hex[:12]}-1"
    a2 = f"it-a-{uuid.uuid4().hex[:12]}-2"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    ash1 = ash2 = inst1 = ""
    try:
        ash1, ash2, inst1 = _seed_work_with_two_authors(driver, ws_id, w_id, author_ids=(a1, a2))
        with driver.session() as session:
            session.run(
                """
                MATCH (w:Work {id: $w_id})
                UNWIND range(1, $n) AS i
                CREATE (m:Method {id: $w_id + '-m-' + toString(i), name: 'M'})
                CREATE (w)-[:USES_METHOD]->(m)
                """,
                w_id=w_id,
                n=55,
            )
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        work_payload = work_graph_neighborhood(
            _StoresStub(neo_store),
            w_id,
            neighbor_limit=12,
            depth=1,
            view="reader",
            prioritize="Method,Dataset,Work,Author,Authorship",
        )
        assert work_payload is not None
        assert work_payload["meta"].get("is_truncated") is True
        center = next(n for n in work_payload["nodes"] if str(n.get("id") or "") == w_id)
        assert int((center.get("properties") or {}).get("authors_count") or 0) == 2
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id STARTS WITH $prefix OR n.id IN $ids DETACH DELETE n",
                prefix=w_id + "-m-",
                ids=[ws_id, w_id, a1, a2, ash1, ash2, inst1],
            )
        driver.close()


@pytest.mark.integration
def test_work_graph_five_authors_aggregator_expand_roundtrip() -> None:
    """Phase 3: ≥4 authors aggregate on work graph; expand returns individual Author nodes."""
    if not _neo4j_available():
        pytest.skip("Neo4j not reachable (integration)")

    settings = get_settings()
    ws_id = f"it-ws-5a-{uuid.uuid4().hex[:12]}"
    w_id = f"it-w-5a-{uuid.uuid4().hex[:10]}"

    driver = GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    neo_store: Neo4jGraphStore | None = None
    author_ids: list[str] = []
    try:
        author_ids = _seed_work_with_five_authors(driver, ws_id, w_id)
        neo_store = Neo4jGraphStore(
            settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password
        )
        work_payload = work_graph_neighborhood(
            _StoresStub(neo_store), w_id, neighbor_limit=200, depth=1, view="reader"
        )
        assert work_payload is not None
        surfaced = surfaced_author_count_reader_work_graph(work_payload, w_id)
        assert surfaced == 5
        agg_id = _aggregator_id(w_id, "Author", "AUTHORED")
        expanded = expand_work_aggregator(_StoresStub(neo_store), w_id, agg_id, limit=20)
        assert expanded is not None
        assert expanded["meta"].get("expanded_aggregator_id") == agg_id
        author_nodes = [n for n in expanded["nodes"] if str(n.get("type") or "") == "Author"]
        assert len(author_nodes) >= 5
    finally:
        if neo_store is not None:
            try:
                neo_store.close()
            except Exception:  # noqa: BLE001
                pass
        ash_ids = [f"{w_id}:ash:{i}" for i in range(1, 6)]
        with driver.session() as session:
            session.run(
                "MATCH (n) WHERE n.id IN $ids DETACH DELETE n",
                ids=[ws_id, w_id, *author_ids, *ash_ids],
            )
        driver.close()
