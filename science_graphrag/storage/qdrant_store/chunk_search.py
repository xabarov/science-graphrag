"""Vector similarity search helpers for Qdrant chunk collections."""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from science_graphrag.storage.qdrant_store.chunk_filters import (
    filter_for_work_id,
    filter_for_workspace_and_work,
)
from science_graphrag.storage.qdrant_store.filters import workspace_filter


def build_chunk_similarity_filter(
    *,
    work_id: str | None,
    work_ids: list[str] | None,
    workspace_id: str | None,
) -> Filter | None:
    """Combine optional workspace scope with work_id / work_ids constraints."""
    ws_scope = (workspace_id or "").strip()
    wid = str(work_id or "").strip()

    if work_ids:
        cleaned = [str(w).strip() for w in work_ids if str(w).strip()]
        if not cleaned:
            return workspace_filter(ws_scope) if ws_scope else None
        work_clause = Filter(
            should=[FieldCondition(key="work_id", match=MatchValue(value=w)) for w in cleaned],
        )
        if ws_scope:
            return Filter(
                must=[
                    FieldCondition(
                        key="workspace_ids",
                        match=MatchAny(any=[ws_scope]),
                    ),
                    work_clause,
                ],
            )
        return work_clause

    if wid and ws_scope:
        return filter_for_workspace_and_work(ws_scope, wid)
    if wid:
        return filter_for_work_id(wid)
    if ws_scope:
        return workspace_filter(ws_scope)
    return None


def map_chunk_query_hit(hit: Any) -> dict[str, Any]:
    """Normalize a scored Qdrant point into the retrieval-facing chunk dict."""
    payload = hit.payload or {}
    fp = payload.get("chunk_fingerprint")
    if not fp:
        fp = str(hit.id)
    return {
        "id": str(hit.id),
        "score": float(hit.score),
        "text": payload.get("text"),
        "work_id": payload.get("work_id"),
        "document_id": payload.get("document_id"),
        "chunk_fingerprint": fp,
        "section_path": payload.get("section_path"),
        "chunk_kind": payload.get("chunk_kind"),
        "language": payload.get("language"),
    }


def query_similar_chunks(
    client: QdrantClient,
    collection: str,
    *,
    vector: list[float],
    limit: int = 8,
    work_id: str | None = None,
    work_ids: list[str] | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return scored hits with payload (text, work_id, chunk metadata)."""
    query_filter = build_chunk_similarity_filter(
        work_id=work_id,
        work_ids=work_ids,
        workspace_id=workspace_id,
    )
    resp = client.query_points(
        collection_name=collection,
        query=vector,
        limit=limit,
        query_filter=query_filter,
        with_payload=True,
    )
    return [map_chunk_query_hit(hit) for hit in resp.points]


__all__ = [
    "build_chunk_similarity_filter",
    "map_chunk_query_hit",
    "query_similar_chunks",
]
