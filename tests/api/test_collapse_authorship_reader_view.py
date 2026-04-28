"""Unit tests for ``collapse_authorship_for_reader_view``."""

from __future__ import annotations

from science_graphrag.api.graph_reader_projection.authorship_collapse import (
    build_authorship_to_reader_author_map,
    collapse_authorship_for_reader_multicenter,
    collapse_authorship_for_reader_view,
)


def test_collapse_authorship_replaces_with_authored_edge() -> None:
    """Native ``OF_AUTHOR`` in edges still produces ``AUTHORED`` with classic ``via``."""
    w1 = "work-1"
    ash = "ash-1"
    a1 = "author-1"
    nodes = [
        {"id": w1, "type": "Work", "label": "Paper"},
        {
            "id": ash,
            "type": "Authorship",
            "node_kind": "AuthorshipReification",
            "properties": {"author_position": 1},
        },
        {"id": a1, "type": "Author", "label": "Alice"},
    ]
    edges = [
        {"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"},
        {"source": ash, "target": a1, "type": "OF_AUTHOR"},
    ]
    nn, ee = collapse_authorship_for_reader_view(nodes, edges, w1)
    assert all(str(n.get("id")) != ash for n in nn)
    authored = [e for e in ee if str(e.get("type") or "").upper() == "AUTHORED"]
    assert len(authored) == 1
    assert authored[0]["source"] == w1
    assert authored[0]["target"] == a1
    assert authored[0].get("via") == ["HAS_AUTHORSHIP", "OF_AUTHOR"]


def test_collapse_authorship_fallback_without_of_author_edge() -> None:
    """When payload has only HAS_AUTHORSHIP, synthesize Author + AUTHORED (enriched path)."""
    w1 = "work-1"
    ash = "ash-1"
    nodes = [
        {"id": w1, "type": "Work", "label": "Paper"},
        {
            "id": ash,
            "type": "Authorship",
            "node_kind": "AuthorshipReification",
            "label": "Bob (#1)",
            "display_label": "Bob (#1)",
            "properties": {"author_position": 1, "raw_affiliation": "MIT"},
        },
    ]
    edges = [{"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"}]
    nn, ee = collapse_authorship_for_reader_view(nodes, edges, w1)
    assert all(str(n.get("id")) != ash for n in nn)
    authored = [e for e in ee if str(e.get("type") or "").upper() == "AUTHORED"]
    assert len(authored) == 1
    assert authored[0]["source"] == w1
    assert authored[0].get("via") == ["HAS_AUTHORSHIP", "enriched_authorship"]
    tgt = str(authored[0].get("target") or "")
    assert tgt.startswith("va:")
    author_nodes = [n for n in nn if str(n.get("type") or "") == "Author"]
    assert len(author_nodes) == 1
    assert str(author_nodes[0].get("id")) == tgt
    assert str(author_nodes[0].get("label") or "") == "Bob"
    raw = author_nodes[0].get("raw") or {}
    assert raw.get("synthesized_from") == "Authorship"


def test_collapse_authorship_uses_author_entity_id_when_no_of_author_edge() -> None:
    """``author_entity_id`` on enriched Authorship yields real Author id + enriched via."""
    w1 = "work-1"
    ash = "ash-1"
    real_author = "author-db-1"
    nodes = [
        {"id": w1, "type": "Work", "label": "Paper"},
        {
            "id": ash,
            "type": "Authorship",
            "label": "Alice (#1)",
            "display_label": "Alice (#1)",
            "properties": {"author_position": 1, "author_entity_id": real_author},
        },
    ]
    edges = [{"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"}]
    nn, ee = collapse_authorship_for_reader_view(nodes, edges, w1)
    authored = [e for e in ee if str(e.get("type") or "").upper() == "AUTHORED"]
    assert len(authored) == 1
    assert authored[0]["target"] == real_author
    assert authored[0].get("via") == ["HAS_AUTHORSHIP", "enriched_authorship"]
    author_nodes = [n for n in nn if str(n.get("id") or "") == real_author]
    assert len(author_nodes) == 1
    assert str(author_nodes[0].get("label") or "") == "Alice"
    assert not author_nodes[0].get("raw")


def test_build_authorship_to_reader_author_map_matches_collapse_of_author() -> None:
    w1 = "work-1"
    ash = "ash-1"
    a1 = "author-1"
    nodes = [
        {"id": w1, "type": "Work"},
        {"id": ash, "type": "Authorship", "node_kind": "AuthorshipReification"},
        {"id": a1, "type": "Author"},
    ]
    edges = [
        {"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"},
        {"source": ash, "target": a1, "type": "OF_AUTHOR"},
    ]
    m = build_authorship_to_reader_author_map(nodes, edges, w1)
    assert m.get(ash) == a1


def test_build_authorship_to_reader_author_map_synthetic_va() -> None:
    w1 = "work-1"
    ash = "ash-1"
    nodes = [
        {"id": w1, "type": "Work"},
        {
            "id": ash,
            "type": "Authorship",
            "label": "Bob (#1)",
            "properties": {"author_position": 1},
        },
    ]
    edges = [{"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"}]
    m = build_authorship_to_reader_author_map(nodes, edges, w1)
    aid = m.get(ash)
    assert aid and str(aid).startswith("va:")
    nn, _ = collapse_authorship_for_reader_view(nodes, edges, w1)
    ids = {str(n.get("id") or "") for n in nn}
    assert aid in ids


def test_multicenter_synthetic_uses_owning_work_not_focal() -> None:
    """Surrogate ``va:`` ids hash with HAS_AUTHORSHIP owner work id (workspace-safe)."""
    w1 = "work-owner-1"
    w2 = "work-owner-2"
    ash1 = "ash-a"
    ash2 = "ash-b"
    nodes = [
        {"id": w1, "type": "Work", "label": "P1"},
        {"id": w2, "type": "Work", "label": "P2"},
        {
            "id": ash1,
            "type": "Authorship",
            "label": "Same (#1)",
            "properties": {"author_position": 1},
        },
        {
            "id": ash2,
            "type": "Authorship",
            "label": "Same (#1)",
            "properties": {"author_position": 1},
        },
    ]
    edges = [
        {"source": w1, "target": ash1, "type": "HAS_AUTHORSHIP"},
        {"source": w2, "target": ash2, "type": "HAS_AUTHORSHIP"},
    ]
    nn, ee = collapse_authorship_for_reader_multicenter(nodes, edges, focal_work_id=w1)
    authored = [e for e in ee if str(e.get("type") or "").upper() == "AUTHORED"]
    assert len(authored) == 2
    by_src = {str(e["source"]): e for e in authored}
    id1 = str(by_src[w1]["target"])
    id2 = str(by_src[w2]["target"])
    assert id1.startswith("va:") and id2.startswith("va:")
    assert id1 != id2
    assert by_src[w1].get("direction") == "outgoing"
    assert by_src[w2].get("direction") == "lateral"


def test_multicenter_rewrites_authorship_affiliated_with_to_author() -> None:
    """Institution edges incident on :Authorship survive collapse as Author–AFFILIATED_WITH."""
    w1 = "work-1"
    ash = "ash-1"
    a1 = "author-1"
    inst = "inst-1"
    nodes = [
        {"id": w1, "type": "Work"},
        {"id": ash, "type": "Authorship", "label": "Bob (#1)"},
        {"id": a1, "type": "Author", "label": "Bob"},
        {"id": inst, "type": "Institution", "node_kind": "Institution", "label": "MIT"},
    ]
    edges = [
        {"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"},
        {"source": ash, "target": a1, "type": "OF_AUTHOR"},
        {"source": ash, "target": inst, "type": "AFFILIATED_WITH"},
    ]
    nn, ee = collapse_authorship_for_reader_multicenter(nodes, edges, focal_work_id=None)
    aff = [e for e in ee if str(e.get("type") or "").upper() == "AFFILIATED_WITH"]
    assert any(str(e.get("source") or "") == a1 and str(e.get("target") or "") == inst for e in aff)


def test_collapse_single_center_matches_multicenter_focal() -> None:
    w1 = "work-1"
    ash = "ash-1"
    nodes = [
        {"id": w1, "type": "Work"},
        {
            "id": ash,
            "type": "Authorship",
            "label": "Bob (#1)",
            "properties": {"author_position": 1},
        },
    ]
    edges = [{"source": w1, "target": ash, "type": "HAS_AUTHORSHIP"}]
    n1, e1 = collapse_authorship_for_reader_view(nodes, edges, w1)
    n2, e2 = collapse_authorship_for_reader_multicenter(nodes, edges, focal_work_id=w1)
    va1 = next(str(e["target"]) for e in e1 if str(e.get("type") or "").upper() == "AUTHORED")
    va2 = next(str(e["target"]) for e in e2 if str(e.get("type") or "").upper() == "AUTHORED")
    assert va1 == va2
