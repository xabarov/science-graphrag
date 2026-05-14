"""Thread-safe ingest job SSE bus publishing (shared by single + batch jobs)."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.ingest_event_bus import BUS


def publish_ingest_job_event(
    *,
    job_id: str,
    parent_job_id: str | None,
    kind: str,
    payload: dict[str, Any],
) -> None:
    """Publish an ingest job event to the in-process bus (mirrors to parent when set)."""
    BUS.publish_threadsafe({"job_id": job_id, "kind": kind, "payload": payload})
    if parent_job_id:
        parent_payload = dict(payload)
        parent_payload["source_job_id"] = job_id
        BUS.publish_threadsafe({"job_id": parent_job_id, "kind": kind, "payload": parent_payload})
