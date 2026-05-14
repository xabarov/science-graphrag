"""Tests for ``expand_work_aggregator`` (work graph aggregator expansion)."""

from __future__ import annotations

from typing import Any

import pytest

from science_graphrag.api.works.graph_neighborhood import (
    _aggregator_id,
    expand_work_aggregator,
)


def test_expand_author_aggregator_uses_reader_without_author_aggregation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Author aggregators use reader re-fetch: raw topology has HAS_AUTHORSHIP, not AUTHORED."""
    captured: dict[str, Any] = {}

    def _fake_work_graph_neighborhood(
        _stores: Any, work_id: str, **kwargs: Any
    ) -> dict[str, Any] | None:
        captured.clear()
        captured.update(kwargs)
        if kwargs.get("view") == "reader":
            return {
                "nodes": [
                    {"id": work_id, "type": "Work", "node_kind": "Work"},
                    {"id": "author-1", "type": "Author", "node_kind": "Author"},
                    {"id": "author-2", "type": "Author", "node_kind": "Author"},
                ],
                "edges": [
                    {
                        "id": "e1",
                        "source": work_id,
                        "target": "author-1",
                        "type": "AUTHORED",
                    },
                    {
                        "id": "e2",
                        "source": work_id,
                        "target": "author-2",
                        "type": "AUTHORED",
                    },
                ],
            }
        return None

    monkeypatch.setattr(
        "science_graphrag.api.works.graph_neighborhood.work_graph_neighborhood",
        _fake_work_graph_neighborhood,
    )

    wid = "work-expand-test-1"
    agg = _aggregator_id(wid, "Author", "AUTHORED")
    out = expand_work_aggregator(object(), wid, agg, limit=10)
    assert out is not None
    assert captured.get("view") == "reader"
    assert captured.get("aggregator_disabled_kinds") == "Author"
    assert out["meta"].get("expanded_aggregator_id") == agg
    assert len(out.get("nodes") or []) >= 2


def test_expand_neighbor_aggregation_contract_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """``expand_work_aggregator`` uses ``work_graph_neighborhood``; aggregation stays disabled."""

    def _fake_work_graph_neighborhood(
        _stores: Any,
        work_id: str,
        **_kwargs: Any,
    ) -> dict[str, Any]:
        return {
            "nodes": [{"id": "w1", "type": "Work", "node_kind": "Work"}],
            "edges": [],
            "meta": {"neighbor_aggregation": "none"},
        }

    monkeypatch.setattr(
        "science_graphrag.api.works.graph_neighborhood.work_graph_neighborhood",
        _fake_work_graph_neighborhood,
    )

    wid = "work-expand-meta-1"
    agg = _aggregator_id(wid, "Work", "CITES")
    out = expand_work_aggregator(object(), wid, agg, limit=5)
    assert out is not None
    assert (out.get("meta") or {}).get("neighbor_aggregation", "none") == "none"
