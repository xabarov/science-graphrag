from __future__ import annotations

from typing import Any

from science_graphrag.api.deps import StoreRegistry


def work_chunks(
    stores: StoreRegistry,
    work_id: str,
    *,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    try:
        total = stores.qdrant_chunks.count_chunks_for_work(work_id=work_id)
    except Exception:  # noqa: BLE001
        return {"items": [], "total": 0, "error": "qdrant_unavailable"}
    accumulated: list[dict[str, Any]] = []
    scroll_offset: int | str | None = None
    cap = min(offset + limit + 100, 5000)
    while len(accumulated) < cap:
        batch, scroll_offset = stores.qdrant_chunks.scroll_chunks_for_work(
            work_id=work_id,
            limit=min(200, cap - len(accumulated)),
            offset=scroll_offset,
        )
        accumulated.extend(batch)
        if scroll_offset is None or not batch:
            break
    slice_rows = accumulated[offset : offset + limit]
    items = [
        {
            "document_id": row.get("document_id"),
            "chunk_fingerprint": row.get("chunk_fingerprint"),
            "section_path": row.get("section_path"),
            "text": (row.get("text") or "")[:8000],
            "order": offset + i,
        }
        for i, row in enumerate(slice_rows)
    ]
    doc_id = items[0]["document_id"] if items else None
    return {"items": items, "total": total, "document_id": doc_id}
