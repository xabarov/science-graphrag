"""Entity dedup collections (methods, datasets, venues, institutions)."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

ENTITY_DEDUP_COLLECTION_NAMES: tuple[str, ...] = ("institutions", "venues", "methods", "datasets")


def ensure_entity_dedup_collections(client: QdrantClient, *, vector_dim: int) -> None:
    """Create entity dedup collections if they do not exist (same dim as chunk/work embeddings)."""
    existing = {c.name for c in client.get_collections().collections}
    for name in ENTITY_DEDUP_COLLECTION_NAMES:
        if name in existing:
            continue
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
        )
