"""Qdrant filter builders shared by chunk read paths."""

from __future__ import annotations

from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue


def filter_for_work_id(work_id: str) -> Filter:
    """Chunks belonging to a single ``work_id``."""
    return Filter(must=[FieldCondition(key="work_id", match=MatchValue(value=work_id))])


def filter_for_workspace_and_work(workspace_id: str, work_id: str) -> Filter | None:
    """Chunks for ``work_id`` scoped to ``workspace_id``; None if either id is empty."""
    ws = (workspace_id or "").strip()
    wid = (work_id or "").strip()
    if not ws or not wid:
        return None
    # Keep workspace_ids before work_id for parity with similarity-search filters.
    return Filter(
        must=[
            FieldCondition(key="workspace_ids", match=MatchAny(any=[ws])),
            FieldCondition(key="work_id", match=MatchValue(value=wid)),
        ],
    )


def filter_for_work_and_fingerprint(work_id: str, chunk_fingerprint: str) -> Filter | None:
    """Single chunk lookup by ``work_id`` + ``chunk_fingerprint``."""
    wid = str(work_id or "").strip()
    fp = str(chunk_fingerprint or "").strip()
    if not wid or not fp:
        return None
    return Filter(
        must=[
            FieldCondition(key="work_id", match=MatchValue(value=wid)),
            FieldCondition(key="chunk_fingerprint", match=MatchValue(value=fp)),
        ],
    )


__all__ = [
    "filter_for_work_and_fingerprint",
    "filter_for_work_id",
    "filter_for_workspace_and_work",
]
