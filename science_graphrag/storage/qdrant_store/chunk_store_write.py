"""Write-side Qdrant chunk vector operations (collection lifecycle, upserts, payload patches)."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from science_graphrag.storage.qdrant_store.chunk_store_common import count_points_exact

if TYPE_CHECKING:
    from science_graphrag.ingestion.chunking import DocumentChunk

logger = logging.getLogger(__name__)


def ensure_chunk_collection(client: QdrantClient, collection: str, vector_dim: int) -> None:
    """Create ``collection`` with cosine vectors when missing."""
    cols = client.get_collections().collections
    names = {c.name for c in cols}
    if collection not in names:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
        )


def upsert_chunks(
    client: QdrantClient,
    collection: str,
    vector_dim: int,
    *,
    work_id: str,
    document_id: str,
    chunks: list[str],
    vectors: np.ndarray,
    embedding_model: str,
) -> None:
    """Upsert legacy flat chunk rows (index-based point ids)."""
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors length mismatch")
    if vectors.size and int(vectors.shape[1]) != vector_dim:
        raise ValueError(
            f"Qdrant chunk vector dim mismatch for collection {collection!r}: "
            f"got {int(vectors.shape[1])}, expected {vector_dim}."
        )
    points: list[PointStruct] = []
    for idx, (text, vec) in enumerate(zip(chunks, vectors, strict=True)):
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{idx}"))
        payload: dict[str, Any] = {
            "work_id": work_id,
            "document_id": document_id,
            "chunk_index": idx,
            "text": text[:8000],
            "embedding_model": embedding_model,
            "workspace_ids": [],
        }
        points.append(
            PointStruct(
                id=pid,
                vector=vec.tolist(),
                payload=payload,
            )
        )
    if points:
        client.upsert(collection_name=collection, points=points)


def upsert_document_chunks(  # pylint: disable=too-many-arguments
    client: QdrantClient,
    collection: str,
    vector_dim: int,
    *,
    work_id: str,
    document_id: str,
    document_chunks: list[DocumentChunk],
    vectors: np.ndarray,
    embedding_model: str,
    workspace_ids: list[str] | None = None,
) -> None:
    """Upsert section-aware chunks with deterministic ids from chunk_fingerprint."""
    # Local import avoids circular import: ingestion.stage_context imports chunk store.
    from science_graphrag.ingestion.chunking import (  # pylint: disable=import-outside-toplevel
        infer_chunk_kind_from_section_path,
    )

    if len(document_chunks) != len(vectors):
        raise ValueError("document_chunks and vectors length mismatch")
    if vectors.size and int(vectors.shape[1]) != vector_dim:
        raise ValueError(
            f"Qdrant chunk vector dim mismatch for collection {collection!r}: "
            f"got {int(vectors.shape[1])}, expected {vector_dim}."
        )
    points: list[PointStruct] = []
    for ch, vec in zip(document_chunks, vectors, strict=True):
        pid = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{document_id}:{ch.chunk_fingerprint}",
            ),
        )
        ws_ids = [str(x).strip() for x in (workspace_ids or []) if str(x).strip()]
        payload: dict[str, Any] = {
            "work_id": work_id,
            "document_id": document_id,
            "chunk_index": ch.chunk_index,
            "chunk_fingerprint": ch.chunk_fingerprint,
            "section_path": ch.section_path,
            "chunk_kind": infer_chunk_kind_from_section_path(ch.section_path),
            "language": "en",
            "overlap_prev": ch.overlap_prev,
            "overlap_next": ch.overlap_next,
            "start_offset": ch.start_offset,
            "end_offset": ch.end_offset,
            "text": ch.text[:8000],
            "embedding_model": embedding_model,
            "workspace_ids": ws_ids,
        }
        points.append(
            PointStruct(
                id=pid,
                vector=vec.tolist(),
                payload=payload,
            ),
        )
    if points:
        client.upsert(collection_name=collection, points=points)


def repoint_work_id_payload(
    client: QdrantClient, collection: str, *, from_work_id: str, to_work_id: str
) -> int:
    """Rewrite ``payload.work_id`` for all points matching ``from_work_id``."""
    if from_work_id == to_work_id:
        return 0
    flt = Filter(
        must=[FieldCondition(key="work_id", match=MatchValue(value=from_work_id))],
    )
    n_before = count_points_exact(client, collection, flt)
    if n_before == 0:
        return 0
    client.set_payload(
        collection_name=collection,
        payload={"work_id": to_work_id},
        points=flt,
        wait=True,
    )
    return n_before


def add_workspace_to_chunks(
    client: QdrantClient, collection: str, *, work_id: str, workspace_id: str
) -> int:
    """Append ``workspace_id`` to ``workspace_ids`` for all points of ``work_id`` (idempotent)."""
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0
    flt = Filter(
        must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
    )
    updated = 0
    offset: int | str | None = None
    while True:
        records, offset = client.scroll(
            collection_name=collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        for rec in records:
            payload = rec.payload or {}
            cur = [str(x).strip() for x in (payload.get("workspace_ids") or []) if str(x).strip()]
            if wid in cur:
                continue
            cur.append(wid)
            client.set_payload(
                collection_name=collection,
                payload={"workspace_ids": cur},
                points=[rec.id],
                wait=True,
            )
            updated += 1
        if offset is None:
            break
    return updated


def remove_workspace_from_chunks(
    client: QdrantClient, collection: str, *, work_id: str, workspace_id: str
) -> int:
    """Remove ``workspace_id`` from ``workspace_ids`` for all points of ``work_id``."""
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0
    flt = Filter(
        must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
    )
    updated = 0
    offset: int | str | None = None
    while True:
        records, offset = client.scroll(
            collection_name=collection,
            scroll_filter=flt,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        for rec in records:
            payload = rec.payload or {}
            cur = [str(x).strip() for x in (payload.get("workspace_ids") or []) if str(x).strip()]
            if wid not in cur:
                continue
            nxt = [x for x in cur if x != wid]
            client.set_payload(
                collection_name=collection,
                payload={"workspace_ids": nxt},
                points=[rec.id],
                wait=True,
            )
            updated += 1
        if offset is None:
            break
    return updated


def add_workspace_to_all_chunks(
    client: QdrantClient,
    collection: str,
    *,
    workspace_id: str,
    progress_log_every: int = 2048,
) -> int:
    """Append ``workspace_id`` to every point in ``collection`` (full-corpus membership)."""
    wid = str(workspace_id or "").strip()
    if not wid:
        return 0
    updated = 0
    offset: int | str | None = None
    while True:
        records, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        if not records:
            break
        for rec in records:
            payload = rec.payload or {}
            cur = [str(x).strip() for x in (payload.get("workspace_ids") or []) if str(x).strip()]
            if wid in cur:
                continue
            cur.append(wid)
            client.set_payload(
                collection_name=collection,
                payload={"workspace_ids": cur},
                points=[rec.id],
                wait=True,
            )
            updated += 1
            if progress_log_every > 0 and updated % progress_log_every == 0:
                logger.info(
                    "add_workspace_to_all_chunks progress workspace_id=%s updated=%d",
                    wid,
                    updated,
                )
        if offset is None:
            break
    return updated


def delete_points_by_document_id(client: QdrantClient, collection: str, *, document_id: str) -> int:
    """Delete all points whose ``document_id`` payload matches; returns deleted count."""
    flt = Filter(
        must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))],
    )
    n = count_points_exact(client, collection, flt)
    if n == 0:
        return 0
    client.delete(
        collection_name=collection,
        points_selector=flt,
        wait=True,
    )
    return n


def delete_points_by_work_id(client: QdrantClient, collection: str, *, work_id: str) -> int:
    """Delete all points for ``work_id``; returns deleted count."""
    flt = Filter(
        must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))],
    )
    n = count_points_exact(client, collection, flt)
    if n == 0:
        return 0
    client.delete(
        collection_name=collection,
        points_selector=flt,
        wait=True,
    )
    return n
