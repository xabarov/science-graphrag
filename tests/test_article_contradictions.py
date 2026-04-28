"""Unit tests for article-grounded CONTRADICTS vocabulary / API shaping."""

from __future__ import annotations

from collections import UserDict

from science_graphrag.api.workspace_graph.projection import (
    edge_dict_from_rel,
    enrich_edges_workspace,
)
from science_graphrag.ontology.article_contradictions import (
    build_edge_contradiction_preview,
    extract_contradiction_rel_api_props,
    sanitize_subtype,
    stable_article_contradiction_id,
)


def test_sanitize_subtype_unknown_becomes_unspecified() -> None:
    assert sanitize_subtype("NOT_A_REAL_TYPE") == "unspecified"
    assert sanitize_subtype("scaling") == "scaling"


def test_stable_article_contradiction_id_ordering() -> None:
    a = stable_article_contradiction_id("b", "a", "fp")
    b = stable_article_contradiction_id("a", "b", "fp")
    assert a == b


def test_extract_contradiction_rel_graph_list_previews_only() -> None:
    raw = {
        "subtype": "era_shift",
        "severity": "nuanced",
        "provenance": "benchmark_materialize",
        "claim_a_text": "One-stage wins.",
        "claim_b_text": "Two-stage wins.",
        "quote_a": "x" * 12,
        "quote_b": "y" * 12,
        "rationale_short": "Different eras.",
    }
    out = extract_contradiction_rel_api_props(raw, for_graph_list=True)
    assert "quote_a_preview" in out
    assert "quote_b_preview" in out
    assert "quote_a" not in out
    assert out.get("has_evidence") is True
    assert out.get("underspecified") is False


def test_extract_contradiction_short_quotes_not_evidence() -> None:
    raw = {
        "subtype": "unspecified",
        "quote_a": "short",
        "quote_b": "also",
        "claim_a_text": "A",
        "claim_b_text": "B",
        "rationale_short": "rationale here ok",
    }
    out = extract_contradiction_rel_api_props(raw, for_graph_list=True)
    assert out.get("has_evidence") is False
    assert out.get("underspecified") is True


def test_build_edge_contradiction_preview_subset() -> None:
    pr = extract_contradiction_rel_api_props(
        {
            "subtype": "post_processing",
            "severity": "direct",
            "provenance": "legacy",
            "has_evidence": True,
        },
        for_graph_list=True,
    )
    pv = build_edge_contradiction_preview(pr)
    assert pv["subtype"] == "post_processing"
    assert "has_evidence" in pv


def test_enrich_edges_workspace_contradicts_summary() -> None:
    nodes = [
        {"id": "w1", "display_label": "Paper A", "label": "Paper A"},
        {"id": "w2", "display_label": "Paper B", "label": "Paper B"},
    ]
    edges = [
        {
            "id": "e1",
            "source": "w1",
            "target": "w2",
            "type": "CONTRADICTS",
            "properties": {
                "subtype": "scaling",
                "has_evidence": True,
                "underspecified": False,
                "severity": "nuanced",
                "provenance": "benchmark_materialize",
            },
        },
    ]
    enrich_edges_workspace(nodes, edges)
    assert "contradicts: scaling" in edges[0]["summary"]
    assert edges[0]["contradiction_preview"]["subtype"] == "scaling"


class _FakeRel(UserDict):
    """Neo4j-like rel: ``dict(rel)`` → properties; ``.type`` → relationship type."""

    @property
    def type(self) -> str:
        return "CONTRADICTS"


def test_edge_dict_from_rel_attaches_contradiction_properties() -> None:
    rel = _FakeRel(
        subtype="scaling",
        quote_a="q" * 10,
        quote_b="p" * 10,
        rationale_short="Compound vs depth.",
        claim_a_text="Depth scales.",
        claim_b_text="Compound scales.",
    )
    edge = edge_dict_from_rel({"id": "a"}, {"id": "b"}, rel, 0)
    assert edge["type"] == "CONTRADICTS"
    assert edge["source"] == "a"
    assert edge["target"] == "b"
    assert "properties" in edge
    assert edge["properties"]["subtype"] == "scaling"
    assert "quote_a_preview" in edge["properties"]
