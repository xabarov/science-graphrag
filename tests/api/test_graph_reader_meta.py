"""Tests for shared reader graph ``meta`` (Phase 0 contract)."""

from __future__ import annotations

from science_graphrag.api.graph_reader_meta import (
    GRAPH_CONTRACT_VERSION,
    enrich_reader_graph_meta,
    graph_mode_from_meta,
)


def test_graph_mode_work_capped() -> None:
    """``work_*`` scopes map to capped standalone neighborhood."""
    assert graph_mode_from_meta({"graph_scope": "work_1hop"}) == "work_capped"
    assert graph_mode_from_meta({"graph_scope": "work_2hop"}) == "work_capped"


def test_graph_mode_workspace_union() -> None:
    """Union semantics from scope or ``mode=union_1hop``."""
    assert graph_mode_from_meta({"graph_scope": "workspace_union_1hop"}) == "workspace_union"
    assert (
        graph_mode_from_meta({"graph_scope": "workspace_v2", "mode": "union_1hop"})
        == "workspace_union"
    )


def test_graph_mode_workspace_neighbors() -> None:
    """Lazy single-node neighbor slice."""
    assert graph_mode_from_meta({"graph_scope": "workspace_neighbors"}) == "workspace_neighbors"


def test_graph_mode_workspace_v2_default() -> None:
    """Default workspace projection bucket."""
    assert (
        graph_mode_from_meta({"graph_scope": "workspace_v2", "mode": "inner_only"})
        == "workspace_v2"
    )


def test_enrich_reader_graph_meta_keys() -> None:
    """Enrich merges Phase 0 keys without clobbering ``neighbor_limit_applied``."""
    meta: dict = {"graph_scope": "work_1hop", "is_truncated": False, "neighbor_limit_applied": 200}
    enrich_reader_graph_meta(
        meta,
        neighbor_limit=200,
        prioritize="Method,Dataset,Work",
        view="reader",
        workspace_id=None,
    )
    assert meta["graph_contract_version"] == GRAPH_CONTRACT_VERSION
    assert meta["graph_mode"] == "work_capped"
    assert meta["neighbor_limit"] == 200
    assert meta["prioritize"] == "Method,Dataset,Work"
    assert meta["view"] == "reader"
    assert meta["workspace_id"] is None
    assert meta["neighbor_limit_applied"] == 200


def test_enrich_sets_neighbor_limit_applied_null_when_absent() -> None:
    """Workspace-style meta gets ``neighbor_limit_applied: null`` when unset."""
    meta = {"graph_scope": "workspace_v2", "mode": "inner_only", "is_truncated": False}
    enrich_reader_graph_meta(
        meta,
        neighbor_limit=None,
        prioritize="Method,Dataset,Work",
        view="reader",
        workspace_id="ws-1",
    )
    assert meta["neighbor_limit_applied"] is None
    assert meta["workspace_id"] == "ws-1"
    assert meta["graph_mode"] == "workspace_v2"


def test_enrich_graph_mode_override() -> None:
    """Explicit ``graph_mode`` wins over ``graph_mode_from_meta``."""
    meta = {"graph_scope": "work_1hop"}
    enrich_reader_graph_meta(
        meta,
        neighbor_limit=50,
        prioritize=None,
        view="raw",
        workspace_id=None,
        graph_mode="work_expand_aggregator",
    )
    assert meta["graph_mode"] == "work_expand_aggregator"
