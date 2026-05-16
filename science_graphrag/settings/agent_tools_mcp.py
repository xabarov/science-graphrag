"""Shared normalization for MCP operator knobs (PATCH + runtime overlay)."""

from __future__ import annotations

from typing import Any

MCP_DENYLIST_MAX_ENTRIES = 32
MCP_DENYLIST_ENTRY_MAX_LEN = 64
MCP_DENYLIST_SNAPSHOT_PREVIEW_MAX = 8


def normalize_mcp_server_denylist(raw: Any) -> list[str]:
    """Return a bounded denylist of non-empty substring fragments."""
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        s = str(item).strip()[:MCP_DENYLIST_ENTRY_MAX_LEN]
        if s:
            cleaned.append(s)
    return cleaned[:MCP_DENYLIST_MAX_ENTRIES]
