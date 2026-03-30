"""Author id canonicalization."""

from __future__ import annotations

from science_graphrag.domain.authorship_ids import canonical_author_node_id


def test_canonical_author_node_id_stable() -> None:
    a = canonical_author_node_id("  Jane   Doe  ")
    b = canonical_author_node_id("jane doe")
    assert a == b


def test_canonical_author_node_id_different_spellings() -> None:
    assert canonical_author_node_id("J. Doe") != canonical_author_node_id("Jane Doe")
