"""Shared reader graph ``meta`` fields (Phase 0 work vs workspace graph contract)."""

from __future__ import annotations

from typing import Any

# Bump when neighbor caps, membership rules, or reader collapse semantics change contractually.
GRAPH_CONTRACT_VERSION: int = 1


def graph_mode_from_meta(meta: dict[str, Any]) -> str:
    """Product-facing graph mode for UI; derived from ``graph_scope`` and workspace ``mode``."""
    scope = str(meta.get("graph_scope") or "")
    mode = str(meta.get("mode") or "").strip().lower()
    if scope in ("work_1hop", "work_2hop"):
        return "work_capped"
    if scope == "workspace_neighbors":
        return "workspace_neighbors"
    if scope == "workspace_union_1hop" or mode == "union_1hop":
        return "workspace_union"
    return "workspace_v2"


def _normalize_workspace_id(workspace_id: str | None) -> str | None:
    if workspace_id is None:
        return None
    stripped = str(workspace_id).strip()
    return stripped or None


def enrich_reader_graph_meta(
    meta: dict[str, Any],
    *,
    neighbor_limit: int | None,
    prioritize: str | None,
    view: str,
    workspace_id: str | None,
    graph_mode: str | None = None,
) -> dict[str, Any]:
    """Mutates and returns ``meta`` with Phase 0 contract fields (idempotent overwrites)."""
    meta["graph_contract_version"] = GRAPH_CONTRACT_VERSION
    meta["neighbor_limit"] = neighbor_limit
    meta["prioritize"] = prioritize
    meta["view"] = str(view or "reader").strip().lower()
    meta["workspace_id"] = _normalize_workspace_id(workspace_id)
    meta["graph_mode"] = graph_mode if graph_mode is not None else graph_mode_from_meta(meta)
    # Work neighborhood sets this before enrich; workspace / expand omit cap semantics.
    if "neighbor_limit_applied" not in meta:
        meta["neighbor_limit_applied"] = None
    return meta
