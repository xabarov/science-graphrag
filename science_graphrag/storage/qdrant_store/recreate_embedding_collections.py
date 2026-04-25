"""Drop and recreate all Qdrant collections used for dense embeddings (one vector size)."""

from __future__ import annotations

from qdrant_client import QdrantClient

from science_graphrag.config import Settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store.author_embeddings import QdrantAuthorEmbeddingStore
from science_graphrag.storage.qdrant_store.chunk_store import recreate_qdrant_chunk_collection
from science_graphrag.storage.qdrant_store.entity_collections import (
    ENTITY_DEDUP_COLLECTION_NAMES,
    ensure_entity_dedup_collections,
)
from science_graphrag.storage.qdrant_store.work_embeddings import QdrantWorkEmbeddingStore


def recreate_all_embedding_collections(settings: Settings) -> int:
    """Delete named collections if present, then create empty ones with ``resolve_embedding_dim``.

    Returns the vector dimension used.
    """

    dim = resolve_embedding_dim(settings=settings)
    client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    existing = {c.name for c in client.get_collections().collections}
    targets = {
        settings.qdrant_collection,
        settings.qdrant_work_embeddings_collection,
        settings.qdrant_claims_collection,
        settings.qdrant_author_embeddings_collection,
        *ENTITY_DEDUP_COLLECTION_NAMES,
    }
    for name in targets:
        if name in existing:
            client.delete_collection(collection_name=name)

    recreate_qdrant_chunk_collection(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        vector_dim=dim,
    )
    QdrantWorkEmbeddingStore(
        settings.qdrant_url,
        settings.qdrant_work_embeddings_collection,
        vector_dim=dim,
    )
    QdrantClaimsStore(
        settings.qdrant_url,
        settings.qdrant_claims_collection,
        vector_dim=dim,
    )
    QdrantAuthorEmbeddingStore(
        settings.qdrant_url,
        settings.qdrant_author_embeddings_collection,
        vector_dim=dim,
    )
    ensure_entity_dedup_collections(client, vector_dim=dim)
    return dim
