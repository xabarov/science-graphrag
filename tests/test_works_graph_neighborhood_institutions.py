"""Tests for split institution attachment helpers in work graph neighborhood."""

from __future__ import annotations

from science_graphrag.api.works.graph_neighborhood_institutions import (
    attach_institutions_raw,
    attach_institutions_reader,
)


def test_attach_institutions_raw_creates_node_and_edge() -> None:
    nodes = [{"id": "ash:1", "type": "Authorship"}]
    edges: list[dict[str, str]] = []
    rows = [
        {
            "ash_id": "ash:1",
            "inst_id": "inst:1",
            "inst_name": "IBM",
            "inst_country": "US",
        }
    ]
    attached = attach_institutions_raw(nodes, edges, rows)
    assert attached == 1
    assert any(n.get("id") == "inst:1" and n.get("type") == "Institution" for n in nodes)
    assert any(e.get("source") == "ash:1" and e.get("target") == "inst:1" for e in edges)


def test_attach_institutions_reader_ignores_rows_without_author_mapping() -> None:
    nodes = [{"id": "author:1", "type": "Author"}]
    edges: list[dict[str, str]] = []
    rows = [{"ash_id": "ash:missing", "inst_id": "inst:2"}]
    attached = attach_institutions_reader(nodes, edges, rows, ash_author_map={})
    assert attached == 0
    assert edges == []
