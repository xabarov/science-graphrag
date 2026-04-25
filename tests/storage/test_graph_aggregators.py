from science_graphrag.api.works.graph_neighborhood import _apply_aggregators


def test_apply_aggregators_collapses_large_group() -> None:
    owner_id = "work-1"
    nodes = [{"id": owner_id, "node_kind": "Work", "type": "Work", "display_label": "Paper A"}]
    for i in range(10):
        nodes.append(
            {
                "id": f"auth-{i}",
                "node_kind": "Authorship",
                "type": "Authorship",
                "display_label": f"Author {i}",
            }
        )
    edges = [
        {
            "id": f"e-{i}",
            "source": owner_id,
            "target": f"auth-{i}",
            "type": "HAS_AUTHORSHIP",
            "display_type": "has authorship",
        }
        for i in range(10)
    ]
    new_nodes, new_edges = _apply_aggregators(owner_id, nodes, edges, threshold=8)
    agg_nodes = [n for n in new_nodes if n["node_kind"] == "Aggregator"]
    assert len(agg_nodes) == 1
    assert agg_nodes[0]["aggregation_hints"]["count"] == 10
    assert len(new_nodes) == 2
    assert any(e["type"] == "AGGREGATED" for e in new_edges)


def test_apply_aggregators_keeps_small_groups() -> None:
    nodes = [
        {"id": "w1", "node_kind": "Work", "type": "Work", "display_label": "Work"},
        {"id": "m1", "node_kind": "Method", "type": "Method", "display_label": "BERT"},
        {"id": "m2", "node_kind": "Method", "type": "Method", "display_label": "GPT"},
        {"id": "m3", "node_kind": "Method", "type": "Method", "display_label": "T5"},
    ]
    edges = [
        {"id": f"e-m{i}", "source": "w1", "target": f"m{i+1}", "type": "USES_METHOD"}
        for i in range(3)
    ]
    new_nodes, _ = _apply_aggregators("w1", nodes, edges, threshold=8)
    assert not any(n["node_kind"] == "Aggregator" for n in new_nodes)
