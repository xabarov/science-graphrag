"""Qdrant filter helpers shared by embedding stores."""

from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchAny


def workspace_filter(workspace_id: str) -> Filter:
    """Filter points that include ``workspace_id`` in payload.workspace_ids."""
    wid = str(workspace_id or "").strip()
    return Filter(
        must=[
            FieldCondition(
                key="workspace_ids",
                match=MatchAny(any=[wid]),
            ),
        ],
    )
