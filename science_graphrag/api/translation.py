"""SSE translation endpoints (LX2 skeleton)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from science_graphrag.config import get_settings
from science_graphrag.utils.llm_semaphore import get_llm_async_semaphore_map

router = APIRouter(tags=["translation"])


async def _sse_stub(*, work_id: str, field: str) -> AsyncIterator[bytes]:
    """Yield two SSE events until real translation streaming is implemented (LX2)."""

    queued = json.dumps({"event": "queued", "work_id": work_id, "field": field})
    yield f"data: {queued}\n\n".encode()
    done = json.dumps({"event": "done", "note": "stub_noop"})
    yield f"data: {done}\n\n".encode()


async def _translation_sse_gated(*, work_id: str, field: str) -> AsyncIterator[bytes]:
    """Cap concurrent translation streams per process (Phase 2B / LX1)."""

    settings = get_settings()
    sem = get_llm_async_semaphore_map(settings)["translation"]
    async with sem:
        async for chunk in _sse_stub(work_id=work_id, field=field):
            yield chunk


@router.post("/works/{work_id}/translate/abstract")
async def translate_abstract_sse(work_id: str) -> StreamingResponse:
    """Stub SSE stream for abstract translation (contract only)."""

    return StreamingResponse(
        _translation_sse_gated(work_id=work_id, field="abstract"),
        media_type="text/event-stream",
    )


@router.post("/works/{work_id}/translate/body")
async def translate_body_sse(work_id: str) -> StreamingResponse:
    """Stub SSE stream for body translation (contract only)."""

    return StreamingResponse(
        _translation_sse_gated(work_id=work_id, field="body"),
        media_type="text/event-stream",
    )
