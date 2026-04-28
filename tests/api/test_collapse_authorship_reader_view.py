"""Unit tests for ``collapse_authorship_for_reader_view``."""

from __future__ import annotations

from science_graphrag.api.graph_reader_projection.authorship_collapse import (
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
