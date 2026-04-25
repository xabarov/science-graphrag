"""Entity dedup collections (methods, datasets, venues, institutions)."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

ENTITY_COLLECTIONS: dict[str, int] = {
    "institutions": 384,
    "venues": 384,
    "methods": 384,
    "datasets": 384,
}


def ensure_entity_dedup_collections(client: QdrantClient) -> None:
    """Create entity dedup collections if they do not exist."""
    existing = {c.name for c in client.get_collections().collections}
    for name, dim in ENTITY_COLLECTIONS.items():
        if name in existing:
            continue
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
