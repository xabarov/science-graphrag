"""Unit tests for retrieval_v1 ranking helpers."""

from __future__ import annotations

from scripts.dual_validate.extractors.retrieval_v1_ranking import (
    format_candidates,
    kendall_order,
    set_metrics,
)


def test_set_metrics_basic() -> None:
    m = set_metrics({"a", "b", "c"}, {"b", "c", "d"})
    assert m["precision"] == round(2 / 3, 3)
    assert m["recall"] == round(2 / 3, 3)


def test_kendall_order_agreement() -> None:
    assert kendall_order(["a", "b", "c"], ["x", "a", "b", "c"]) == 1.0


def test_format_candidates_line() -> None:
    inv = {"w1": {"title": "T", "year": "2020"}}
    assert "w1" in format_candidates(["w1"], inv)
    assert "2020" in format_candidates(["w1"], inv)
