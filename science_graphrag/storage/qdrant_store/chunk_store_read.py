"""Read-side Qdrant chunk operations (scroll, counts, similarity search)."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter

from science_graphrag.storage.qdrant_store.chunk_filters import (
    filter_for_work_and_fingerprint,
    filter_for_work_id,
    filter_for_workspace_and_work,
)
from science_graphrag.storage.qdrant_store.chunk_search import query_similar_chunks
from science_graphrag.storage.qdrant_store.chunk_store_common import count_points_exact


def scroll_points_payload_only(
    client: QdrantClient,
    collection: str,
    *,
    limit: int,
    offset: int | str | None = None,
) -> tuple[list[Any], int | str | None]:
    """Scroll points in ``collection`` returning payloads only (diagnostics)."""
    return client.scroll(
        collection_name=collection,
        limit=limit,
        offset=offset,
        with_payload=True,
        with_vectors=False,
    )


def search_similar_chunks(
    client: QdrantClient,
    collection: str,
    *,
    vector: list[float],
    limit: int = 8,
    work_id: str | None = None,
    work_ids: list[str] | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """Vector similarity search over chunk payloads (delegates to ``chunk_search``)."""
    return query_similar_chunks(
        client,
        collection,
        vector=vector,
        limit=limit,
        work_id=work_id,
        work_ids=work_ids,
        workspace_id=workspace_id,
    )


def count_chunks_for_work(client: QdrantClient, collection: str, *, work_id: str) -> int:
    """Exact count of chunk points for a single ``work_id``."""
    flt = filter_for_work_id(work_id)
    return count_points_exact(client, collection, flt)


def count_chunks_for_workspace_work(
    client: QdrantClient, collection: str, *, workspace_id: str, work_id: str
) -> int:
    """Exact count of chunk points for ``work_id`` scoped to ``workspace_id``."""
    flt = filter_for_workspace_and_work(workspace_id, work_id)
    if flt is None:
        return 0
    return count_points_exact(client, collection, flt)


def scroll_chunks_for_work(
    client: QdrantClient,
    collection: str,
    *,
    work_id: str,
    limit: int = 50,
    offset: int | str | None = None,
) -> tuple[list[dict[str, Any]], int | str | None]:
    """Scroll chunk payloads for one work (stable scroll order)."""
    flt: Filter = filter_for_work_id(work_id)
    records, next_offset = client.scroll(
        collection_name=collection,
        scroll_filter=flt,
        limit=limit,
        offset=offset,
        with_payload=True,
    )
    out: list[dict[str, Any]] = []
    for rec in records:
        payload = rec.payload or {}
        out.append(
            {
                "document_id": payload.get("document_id"),
                "chunk_fingerprint": payload.get("chunk_fingerprint"),
                "section_path": payload.get("section_path"),
                "text": payload.get("text"),
                "chunk_index": payload.get("chunk_index"),
            },
        )
    return out, next_offset


def get_chunk_text_by_work_and_fingerprint(
    client: QdrantClient,
    collection: str,
    *,
    work_id: str,
    chunk_fingerprint: str,
) -> str | None:
    """Return stored chunk text for a work + fingerprint (citation enrichment)."""
    flt = filter_for_work_and_fingerprint(work_id, chunk_fingerprint)
    if flt is None:
        return None
    records, _ = client.scroll(
        collection_name=collection,
        scroll_filter=flt,
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if not records:
        return None
    payload = records[0].payload or {}
    text = payload.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()[:8000]
    return None
