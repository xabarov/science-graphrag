"""Display label contract checks for works graph payload helpers."""

from __future__ import annotations

from science_graphrag.api.graph_display import (
    EDGE_DISPLAY_TYPE_RAW,
    compute_node_display,
    edge_display_type,
)
from science_graphrag.api.works.graph_neighborhood import _append_neighbor_edge


def test_compute_node_display_humanized_fallbacks() -> None:
    work = compute_node_display("Work", "", {})
    assert work["display_label"] == "Untitled work"
    assert work["subtitle"] == "Work"

    author = compute_node_display("Author", "", {})
    assert author["display_label"] == "Unnamed author"

    institution = compute_node_display("Institution", "", {})
    assert institution["display_label"] == "Unnamed institution"

    venue = compute_node_display("Venue", "", {})
    assert venue["display_label"] == "Unknown venue"

    method = compute_node_display("Method", "", {})
    assert method["display_label"] == "Unnamed method"

    dataset = compute_node_display("Dataset", "", {})
    assert dataset["display_label"] == "Unnamed dataset"


def test_compute_node_display_institution_and_venue_subtitles_from_props() -> None:
    institution = compute_node_display("Institution", "MIT", {"country": "US"})
    assert institution["display_label"] == "MIT"
    assert institution["subtitle"] == "Institution · US"

    venue = compute_node_display("Venue", "ACL", {"venue_type": "conference"})
    assert venue["display_label"] == "ACL"
    assert venue["subtitle"] == "Venue · conference"

    venue_with_issn = compute_node_display("Venue", "JMLR", {"issn": "1532-4435"})
    assert venue_with_issn["subtitle"] == "Venue · 1532-4435"


def test_compute_node_display_authorship_prefers_author_name() -> None:
    rendered = compute_node_display(
        "Authorship",
        "",
        {},
        authorship_extra={
            "author_position": 1,
            "author_name": "Wei Liu",
            "raw_affiliation": "IBM Research",
            "institution_name": "",
            "is_corresponding": False,
        },
    )
    assert rendered["display_label"] == "Wei Liu (#1)"
    assert rendered["subtitle"] == "Author #1 · IBM Research"
    assert rendered["properties"]["author_position"] == 1
    assert rendered["properties"]["raw_affiliation"] == "IBM Research"


def test_compute_node_display_authorship_fallbacks_without_author_name() -> None:
    rendered = compute_node_display(
        "Authorship",
        "",
        {},
        authorship_extra={"author_position": 2},
    )
    assert rendered["display_label"] == "Author #2"
    assert rendered["subtitle"] == "Author #2"


def test_append_neighbor_edge_does_not_use_uuid_in_display_label() -> None:
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    rec = {
        "labs": ["Authorship"],
        "nid": "b240ca79-6dc1-49ec-90c7-acce907439d1:ash:1",
        "nlabel": "",
        "n_pub_year": None,
        "n_doi": "",
        "n_arxiv": "",
        "n_venue": "",
        "n_ash_pos": 1,
        "n_ash_author": "",
        "n_ash_aff": "",
        "n_ash_inst": "",
        "n_ash_corr": None,
        "src_id": "w1",
        "tgt_id": "b240ca79-6dc1-49ec-90c7-acce907439d1:ash:1",
        "rt": "HAS_AUTHORSHIP",
    }
    _append_neighbor_edge(nodes, edges, "w1", rec)
    node = nodes[0]
    assert node["display_label"] == "Author #1"
    assert node["node_kind"] == "AuthorshipReification"
    assert ":ash:" not in str(node["display_label"])


def test_edge_display_type_dictionary() -> None:
    for rel_type, expected in EDGE_DISPLAY_TYPE_RAW.items():
        assert edge_display_type(rel_type) == expected
