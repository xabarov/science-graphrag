"""Unit tests for ``compute_authorship_projection_meta`` (work graph debug meta)."""

from __future__ import annotations

from science_graphrag.api.graph_reader_projection.authorship_meta import (
    compute_authorship_projection_meta,
)


def test_authorship_projection_native() -> None:
    """All ``AUTHORED`` targets are non-``va:`` ids."""
    wid = "work-1"
    edges = [
        {"source": wid, "target": "author-a", "type": "AUTHORED"},
        {"source": wid, "target": "author-b", "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta(wid, edges) == "native"


def test_authorship_projection_synthesized() -> None:
    """Only ``va:`` synthetic author ids."""
    wid = "work-2"
    edges = [
        {"source": wid, "target": "va:" + "a" * 20, "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta(wid, edges) == "synthesized"


def test_authorship_projection_mixed() -> None:
    """Mix of real and ``va:`` targets."""
    wid = "work-3"
    edges = [
        {"source": wid, "target": "author-real", "type": "AUTHORED"},
        {"source": wid, "target": "va:" + "b" * 20, "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta(wid, edges) == "mixed"


def test_authorship_projection_none() -> None:
    """No ``AUTHORED`` edges from center."""
    wid = "work-4"
    edges = [
        {"source": wid, "target": "m1", "type": "USES_METHOD"},
    ]
    assert compute_authorship_projection_meta(wid, edges) == "none"


def test_authorship_projection_incoming_edge() -> None:
    """Incoming ``AUTHORED`` toward center still counts as native."""
    wid = "work-5"
    edges = [
        {"source": "author-z", "target": wid, "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta(wid, edges) == "native"


def test_authorship_projection_workspace_scope_native() -> None:
    edges = [
        {"source": "w-a", "target": "author-1", "type": "AUTHORED"},
        {"source": "w-b", "target": "author-2", "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta("", edges, workspace_scope=True) == "native"


def test_authorship_projection_workspace_scope_mixed() -> None:
    edges = [
        {"source": "w-a", "target": "author-1", "type": "AUTHORED"},
        {"source": "w-b", "target": "va:" + "c" * 20, "type": "AUTHORED"},
    ]
    assert compute_authorship_projection_meta("", edges, workspace_scope=True) == "mixed"
