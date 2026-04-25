"""Display label checks for workspace graph helpers."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.graph_display import enrich_authorship_nodes


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
