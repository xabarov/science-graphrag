"""Display label checks for workspace graph helpers."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.graph_reader_projection.authorship_enrich import enrich_authorship_nodes
from science_graphrag.api.workspace_graph.projection import apply_workspace_node_kind


class _FakeSession:
    def run(self, _query: str, **_params: Any):
        return [
            {
                "aid": "ash-1",
                "pos": 1,
                "raw_aff": "IBM Research",
                "corr": False,
                "auth_name": "Wei Liu",
                "inst_name": "",
            },
        ]


def test_enrich_authorship_nodes_rewrites_display_fields() -> None:
    nodes = [
        {
            "id": "ash-1",
            "type": "Authorship",
            "label": "Authorship",
            "display_label": "Authorship",
            "subtitle": "Authorship",
            "properties": {},
        },
    ]
    enrich_authorship_nodes(_FakeSession(), nodes)  # type: ignore[arg-type]
    node = nodes[0]
    assert node["display_label"] == "Wei Liu (#1)"
    assert node["subtitle"] == "Author #1 · IBM Research"
    assert node["properties"]["author_position"] == 1


def test_apply_workspace_node_kind_for_work_membership() -> None:
    nodes = [
        {"id": "w1", "type": "Work", "workspace_membership": "internal", "node_kind": "Work"},
        {"id": "w2", "type": "Work", "workspace_membership": "external", "node_kind": "Work"},
        {"id": "ash", "type": "Authorship", "node_kind": "Authorship"},
    ]
    apply_workspace_node_kind(nodes)
    assert nodes[0]["node_kind"] == "WorkInternal"
    assert nodes[1]["node_kind"] == "WorkExternal"
    assert nodes[2]["node_kind"] == "AuthorshipReification"
