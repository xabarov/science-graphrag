"""Unit tests for deterministic GOST-like lines."""

from __future__ import annotations

from science_graphrag.agent.bibliography.gost import (
    build_entries_from_work_cards,
    format_gost_article_line,
)


def test_conference_event_and_pages() -> None:
    line = format_gost_article_line(
        authors=["A. Author"],
        title="My Paper",
        venue="NeurIPS",
        year=2020,
        doi="10.1/2",
        event="Neural Information Processing Systems",
        pages="100–102",
    )
    assert "Neural Information Processing" in line
    assert "100" in line


def test_build_entries_from_cards_includes_event() -> None:
    rows = [
        {
            "title": "T",
            "year": 2019,
            "doi": None,
            "authors": ["X"],
            "venue": "Proc. CVPR",
            "event": "CVPR 2019",
            "pages": "1–2",
        }
    ]
    out = build_entries_from_work_cards(rows)
    assert len(out) == 1
    assert "CVPR" in out[0]
