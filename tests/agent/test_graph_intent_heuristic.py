from __future__ import annotations

from science_graphrag.agent.coordination.deterministic import _graph_intent_heuristic


def test_graph_intent_false_on_citations_boilerplate() -> None:
    q = (
        "Compare evidence for two different object-detection works in this workspace: "
        "use find_works twice with different title keywords (for example 'YOLO' vs "
        "'Faster R-CNN'), then call paper_profile for two distinct work_ids from the "
        "results. Finish with final_answer and citations for both work_ids."
    )
    assert _graph_intent_heuristic(q) is False


def test_graph_intent_true_on_citation_chain() -> None:
    assert (
        _graph_intent_heuristic(
            "What is the citation chain between paper A and paper B in this workspace?"
        )
        is True
    )


def test_graph_intent_true_on_who_cited() -> None:
    assert _graph_intent_heuristic("Who cited this paper in the workspace?") is True


def test_graph_intent_true_on_explicit_cypher() -> None:
    assert _graph_intent_heuristic("Run a cypher query to list METHOD edges for work w1") is True
