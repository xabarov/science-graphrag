"""Shared helpers for OD manifest / gap-audit CLI scripts."""

from __future__ import annotations

from typing import Any

from eval.chat_agent.od_workspace_manifest import build_od_workspace_manifest
from science_graphrag.api.deps import close_store_registry, init_store_registry
from science_graphrag.config import get_settings


def build_od_workspace_manifest_live(*, workspace_id: str, lane: str = "rich_od") -> dict[str, Any]:
    """Open store registry, build manifest, close stores (for thin ``scripts/`` CLIs)."""
    settings = get_settings()
    stores = init_store_registry(settings)
    try:
        return build_od_workspace_manifest(
            workspace_id=workspace_id.strip(),
            stores=stores,
            settings=settings,
            lane=(lane or "rich_od").strip() or "rich_od",
        )
    finally:
        close_store_registry()
