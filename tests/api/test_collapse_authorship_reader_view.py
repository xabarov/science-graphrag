from __future__ import annotations

from science_graphrag.api.works.graph_neighborhood import collapse_authorship_for_reader_view


def test_collapse_authorship_replaces_with_authored_edge() -> None:
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
