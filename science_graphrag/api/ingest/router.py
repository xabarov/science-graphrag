"""FastAPI router for ingest jobs and event streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError
from sse_starlette.sse import EventSourceResponse

from science_graphrag.api.ingest_event_bus import BUS

from .dispatcher import _refresh_parent_job, job_to_dict
from .registry import _registry

router = APIRouter(tags=["ingest"])


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str) -> dict[str, Any]:
    registry = _registry()
    try:
        rec = registry.get(job_id)
    except OperationalError:
        raise HTTPException(status_code=404, detail="job_not_found") from None
    if not rec:
        raise HTTPException(status_code=404, detail="job_not_found")
    if rec.kind == "batch_parent":
        _refresh_parent_job(job_id)
        rec = registry.get(job_id) or rec
    return job_to_dict(rec)


def _parse_last_event_id(raw: str | None) -> int:
    if not raw:
        return 0
    try:
        return max(0, int(str(raw).strip()))
    except Exception:
        return 0


def _is_terminal_status(status: str | None) -> bool:
    return str(status or "").strip().lower() in {"completed", "failed"}


def _to_sse_event(seq: int, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(seq), "event": str(kind), "data": json.dumps(payload, ensure_ascii=True)}


async def _job_events_stream(job_id: str, request: Request) -> AsyncIterator[dict[str, Any]]:
    registry = _registry()
    rec = registry.get(job_id)
    if not rec:
        return
    yield _to_sse_event(0, "snapshot", {"job": job_to_dict(rec)})
    last_seq = _parse_last_event_id(request.headers.get("last-event-id"))
    if last_seq > 0:
        for seq, event in BUS.replay_from(job_id, last_seq):
            yield _to_sse_event(seq, event["kind"], event["payload"])
    async for seq, event in BUS.subscribe(job_id):
        if await request.is_disconnected():
            break
        yield _to_sse_event(seq, event["kind"], event["payload"])
        if event["kind"] == "terminal":
            break
        if rec.kind == "batch_parent" and event["kind"] == "batch_progress":
            refreshed = registry.get(job_id)
            if refreshed and _is_terminal_status(refreshed.status):
                break


@router.get("/ingest/jobs/{job_id}/events")
async def get_ingest_job_events(job_id: str, request: Request) -> EventSourceResponse:
    registry = _registry()
    try:
        rec = registry.get(job_id)
    except OperationalError:
        raise HTTPException(status_code=404, detail="job_not_found") from None
    if not rec:
        raise HTTPException(status_code=404, detail="job_not_found")
    if rec.kind == "batch_parent":
        _refresh_parent_job(job_id)
    return EventSourceResponse(
        _job_events_stream(job_id, request),
        ping=15,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


class IngestStubBody(BaseModel):
    arxiv_id: str | None = None
    doi: str | None = None


@router.post("/ingest/arxiv")
def ingest_arxiv_stub(_body: IngestStubBody) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="ingest_arxiv_not_implemented_upload_pdf_or_md",
    )


@router.post("/ingest/doi")
def ingest_doi_stub(_body: IngestStubBody) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="ingest_doi_not_implemented_upload_pdf_or_md",
    )


@router.post("/ingest/pdf")
def ingest_pdf_stub() -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="ingest_pdf_use_workspace_upload",
    )
