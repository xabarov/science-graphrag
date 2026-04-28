"""Contract tests for work-graph reader-collapse vs authorship (Phase 1).

See ``docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md``.
Reader view must surface ``AUTHORED`` / ``Author`` when the neighbor payload
has ``HAS_AUTHORSHIP`` only (no ``OF_AUTHOR`` edges). Raw view stays unchanged.
"""

from __future__ import annotations

from typing import Any

from science_graphrag.api.works.graph_neighborhood import (
    _work_graph_neighborhood_payload,
)


class _Single:
    """Neo4j row wrapper used by ``_FakeResult``."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Return row field or default."""
        return self._data.get(key, default)


class _FakeResult:
    """Iterable query result with ``single()`` for one-row queries."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def single(self) -> _Single | None:
        """Return first row or None."""
        if not self._rows:
            return None
        return _Single(self._rows[0])

    def __iter__(self):
        """Yield ``_Single`` wrappers for each row."""
        for row in self._rows:
            yield _Single(row)


CENTER_ID = "w-main"
ASH_IDS = (f"{CENTER_ID}:ash:1", f"{CENTER_ID}:ash:2", f"{CENTER_ID}:ash:3")
ASH_AUTHOR_NAMES = ("Wei Liu", "Jia Deng", "Anna Mu")
ASH_POSITIONS = (1, 2, 3)
ASH_AFF = ("IBM Research", "Stanford", "")


def _authorship_neighbor_row(idx: int) -> dict[str, Any]:
    """Row shape produced by ``_work_neighbors_rows`` for an Authorship neighbor.

    ``OPTIONAL MATCH (n)-[:OF_AUTHOR]->(auth)`` populates ``n_ash_author``
    on the row, but the row is still typed ``Authorship`` and the relation
    ``rt`` is ``HAS_AUTHORSHIP``; no ``OF_AUTHOR`` edge is emitted.
    """
    return {
        "nid": ASH_IDS[idx],
        "labs": ["Authorship"],
        "rt": "HAS_AUTHORSHIP",
        "nlabel": "",
        "src_id": CENTER_ID,
        "tgt_id": ASH_IDS[idx],
        "n_pub_year": None,
        "n_doi": "",
        "n_arxiv": "",
        "n_venue": "",
        "n_country": "",
        "n_venue_type": "",
        "n_issn": "",
        "n_workspace_membership": "",
        "n_ash_pos": ASH_POSITIONS[idx],
        "n_ash_aff": ASH_AFF[idx],
        "n_ash_corr": False,
        "n_ash_author": ASH_AUTHOR_NAMES[idx],
        "n_ash_inst": "",
        "n_auth_id": "",
    }


class _FakeSession:  # pylint: disable=too-few-public-methods
    """Reproduces the Cypher query branches used by ``_work_graph_neighborhood_payload``.

    Critically, no branch returns rows with ``rt == 'OF_AUTHOR'`` and no Author
    label rows: the production neighbor query never emits them either, even
    though the optional match populates ``n_ash_author`` for display.
    """

    def run(
        self, query: str, **params: Any
    ) -> _FakeResult:  # pylint: disable=too-many-return-statements
        """Dispatch canned rows by Cypher substring (mirrors Neo4j driver)."""
        if "RETURN w.id AS wid" in query:
            return _FakeResult(
                [
                    {
                        "wid": CENTER_ID,
                        "wtitle": "Main Work",
                        "wyear": 2024,
                        "wdoi": "",
                        "warxiv": "",
                        "wvenue": "",
                        "has_semantic": False,
                    }
                ]
            )
        if "cites_in_count" in query:
            return _FakeResult(
                [
                    {
                        "cites_in_count": 0,
                        "cites_out_count": 0,
                        "authors_count": len(ASH_IDS),
                    }
                ]
            )
        if "RETURN count(r) AS c" in query:
            return _FakeResult([{"c": len(ASH_IDS)}])
        if "WITH labels(n) AS labs, count(r) AS c" in query:
            return _FakeResult([{"kind": "Authorship", "c": len(ASH_IDS)}])
        if (
            "MATCH (w:Work {id: $id})-[r]-(n)" in query
            and "OPTIONAL MATCH (n)-[:OF_AUTHOR]" in query
        ):
            if params.get("prefer_priority"):
                return _FakeResult([])
            return _FakeResult([_authorship_neighbor_row(i) for i in range(len(ASH_IDS))])
        if "UNWIND $h1 AS wid" in query:
            return _FakeResult([])
        if "UNWIND $ids AS aid" in query:
            return _FakeResult(
                [
                    {
                        "aid": ASH_IDS[i],
                        "pos": ASH_POSITIONS[i],
                        "raw_aff": ASH_AFF[i],
                        "corr": False,
                        "auth_name": ASH_AUTHOR_NAMES[i],
                        "inst_name": "",
                    }
                    for i in range(len(ASH_IDS))
                ]
            )
        return _FakeResult([])


def _payload(view: str) -> dict[str, Any]:
    payload = _work_graph_neighborhood_payload(
        _FakeSession(),  # type: ignore[arg-type]
        CENTER_ID,
        neighbor_limit=200,
        depth=1,
        prioritize="Method,Dataset,Work",
        view=view,
        include_claims=False,
    )
    assert payload is not None
    return payload


def _author_like_node_count(payload: dict[str, Any]) -> int:
    """Count nodes that the UI would treat as authors (real or synthesized).

    Phase 1 may choose Option A (real ``Author`` nodes via emitted ``OF_AUTHOR``)
    or Option B (synthesized author surrogates derived from enriched
    ``Authorship`` props). Either is acceptable; this helper accepts both.
    """
    cnt = 0
    for n in payload.get("nodes") or []:
        ntype = str(n.get("type") or "")
        nkind = str(n.get("node_kind") or "")
        if ntype == "Author" or nkind == "Author":
            cnt += 1
    return cnt


def _authored_edges_from_center(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e
        for e in (payload.get("edges") or [])
        if str(e.get("type") or "").upper() == "AUTHORED"
        and str(e.get("source") or "") == CENTER_ID
    ]


def _authorship_node_ids(payload: dict[str, Any]) -> list[str]:
    return [
        str(n.get("id") or "")
        for n in (payload.get("nodes") or [])
        if str(n.get("type") or "") == "Authorship"
    ]


def test_reader_view_emits_authored_for_each_authorship() -> None:
    """Reader view must surface every authorship as an Author or an AUTHORED edge."""
    payload = _payload(view="reader")
    surfaced = max(_author_like_node_count(payload), len(_authored_edges_from_center(payload)))
    assert surfaced == len(ASH_IDS), (
        f"Expected {len(ASH_IDS)} surfaced authors (Author nodes or AUTHORED "
        f"edges from center), got {surfaced}. Nodes: "
        f"{[(n.get('id'), n.get('type'), n.get('node_kind')) for n in payload['nodes']]}; "
        f"edges: {[(e.get('source'), e.get('type'), e.get('target')) for e in payload['edges']]}"
    )


def test_reader_view_does_not_silently_drop_authorship_without_replacement() -> None:
    """Either Authorship remains in the payload or AUTHORED edges replace it.

    Encodes the architectural contract regardless of the chosen Phase 1
    representation (Option A native Author nodes vs Option B synthesized
    surrogates).
    """
    payload = _payload(view="reader")
    keeps_authorship = bool(_authorship_node_ids(payload))
    has_authored = bool(_authored_edges_from_center(payload))
    assert keeps_authorship or has_authored, (
        "Reader view dropped all Authorship nodes and produced no AUTHORED edges; "
        "authors are invisible to the UI."
    )


def test_reader_view_authors_count_property_consistent_with_surfaced_authors() -> None:
    """``properties.authors_count`` on the center Work must match what is rendered."""
    payload = _payload(view="reader")
    center = next((n for n in payload["nodes"] if str(n.get("id")) == CENTER_ID), None)
    assert center is not None, "center Work missing from payload"
    expected = int((center.get("properties") or {}).get("authors_count") or 0)
    surfaced = max(_author_like_node_count(payload), len(_authored_edges_from_center(payload)))
    assert surfaced == expected, (
        f"properties.authors_count={expected} but surfaced authors={surfaced}; "
        f"reader view diverges from the count it advertises."
    )


def test_raw_view_preserves_authorship_and_has_authorship() -> None:
    """Locks the current raw-view shape so Phase 1 cannot accidentally regress it."""
    payload = _payload(view="raw")
    ash_ids = _authorship_node_ids(payload)
    assert len(ash_ids) == len(
        ASH_IDS
    ), f"Expected {len(ASH_IDS)} Authorship nodes in raw view, got {len(ash_ids)}: {ash_ids}"
    has_authorship_edges = [
        e
        for e in (payload.get("edges") or [])
        if str(e.get("type") or "").upper() == "HAS_AUTHORSHIP"
        and str(e.get("source") or "") == CENTER_ID
    ]
    assert len(has_authorship_edges) == len(ASH_IDS), (
        f"Expected {len(ASH_IDS)} HAS_AUTHORSHIP edges from center in raw view, "
        f"got {len(has_authorship_edges)}"
    )
    assert not _authored_edges_from_center(
        payload
    ), "Raw view must not synthesize AUTHORED edges; that is reader-view behavior."
