"""Shared Qdrant helpers for chunk store read/write modules."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Filter


def count_points_exact(client: QdrantClient, collection: str, flt: Filter) -> int:
    """Return exact point count for ``collection`` matching ``flt``."""
    res = client.count(
        collection_name=collection,
        count_filter=flt,
        exact=True,
    )
    return int(res.count)
