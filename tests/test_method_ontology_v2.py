"""Regression tests for Method ontology v2 (ADR 023)."""

from __future__ import annotations

from science_graphrag.api.workspace_graph.projection import node_dict_from_neo
from science_graphrag.domain.semantic_models import SemanticMethodV1
from science_graphrag.ingestion.method_consolidation import consolidate_document_methods


def test_consolidate_document_methods_collapses_near_duplicate_names() -> None:
    a = SemanticMethodV1(
        name="FPN",
        aliases=["Feature Pyramid Network"],
        description_short="Pyramid features",
        confidence=0.9,
        evidence=[],
    )
    b = SemanticMethodV1(
        name="Feature Pyramid Network",
        aliases=[],
        description_short="Multi-scale",
        confidence=0.85,
        evidence=[],
    )
    out = consolidate_document_methods([a, b])
    assert len(out) == 1
    assert "FPN" in out[0].name or "Feature Pyramid" in out[0].name
    assert len(out[0].aliases) >= 1


def test_node_dict_from_neo_method_surfaces_markdown() -> None:
    class _MethodNode(dict):
        labels = ["Method"]

    raw = _MethodNode(
        {
            "id": "mid-test",
            "name": "DETR",
            "description_short": "Transformer detector",
            "description_markdown": "## DETR\nEnd-to-end object detection.",
            "method_kind": "architecture",
            "aliases": ["Detection Transformer"],
        },
    )

    node = node_dict_from_neo(raw)
    assert node is not None
    props = node["properties"]
    assert "DETR" in (node.get("display_label") or node.get("label") or "")
    assert props.get("description_markdown", "").startswith("## DETR")
