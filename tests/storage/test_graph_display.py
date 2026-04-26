"""Unit tests for graph_display projections (Wave GR2)."""

from science_graphrag.api.graph_display import (
    edge_display_type,
    node_kind_priority,
    resolve_node_kind,
)


def test_edge_display_type_semantic() -> None:
    assert edge_display_type("HAS_AUTHORSHIP") == "authored by"
    assert edge_display_type("OF_AUTHOR") == "is author of"
    assert edge_display_type("CITES") == "cites"
    assert edge_display_type("USES_METHOD") == "uses method"


def test_edge_display_type_reader_view() -> None:
    assert edge_display_type("CITES", view="reader") == "references"
    assert edge_display_type("CITES", view="raw") == "cites"
    assert edge_display_type("HAS_AUTHORSHIP", view="reader") == "listed as author"


def test_edge_display_type_unknown_fallback() -> None:
    assert edge_display_type("SOME_RELATION") == "some relation"


def test_resolve_node_kind_authorship() -> None:
    assert resolve_node_kind("Authorship") == "AuthorshipReification"


def test_resolve_node_kind_work_internal() -> None:
    assert resolve_node_kind("Work", workspace_membership="internal") == "WorkInternal"


def test_resolve_node_kind_work_external() -> None:
    assert resolve_node_kind("Work", workspace_membership="external") == "WorkExternal"


def test_resolve_node_kind_work_unknown() -> None:
    assert resolve_node_kind("Work") == "Work"


def test_node_kind_priority_order() -> None:
    """Method and Dataset survive truncation before Venue/Institution."""
    assert node_kind_priority("Method") < node_kind_priority("Institution")
    assert node_kind_priority("Dataset") < node_kind_priority("AuthorshipReification")
    assert node_kind_priority("Work") < node_kind_priority("Author")
