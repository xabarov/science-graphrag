"""In-process buffer for Agent v2 SSE runs (replay + live fan-out for client resume)."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

RunStatus = Literal["running", "completed", "failed", "cancelled"]

_DEFAULT_TTL_S = 3600.0
_MAX_EVENTS_PER_RUN = 500


@dataclass
class BufferedSseEvent:
    seq: int
    data: str


@dataclass
class AgentRunRecord:
    run_id: str
    thread_id: str | None
    workspace_id: str | None
    status: RunStatus = "running"
    events: list[BufferedSseEvent] = field(default_factory=list)
    subscribers: list[asyncio.Queue[BufferedSseEvent | None]] = field(default_factory=list)
    created_at: float = field(default_factory=time.monotonic)
    updated_at: float = field(default_factory=time.monotonic)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


class AgentRunBuffer:
    """Process-local run event store (MVP; optional Redis extension later)."""

    def __init__(
        self,
        *,
        ttl_seconds: float = _DEFAULT_TTL_S,
        max_events_per_run: int = _MAX_EVENTS_PER_RUN,
    ) -> None:
        self._ttl = float(ttl_seconds)
        self._max_events = int(max_events_per_run)
        self._runs: dict[str, AgentRunRecord] = {}
        self._global_lock = asyncio.Lock()

    async def create_run(
        self,
        *,
        thread_id: str | None = None,
        workspace_id: str | None = None,
    ) -> str:
        run_id = f"run-{uuid.uuid4().hex}"
        rec = AgentRunRecord(
            run_id=run_id,
            thread_id=(thread_id or "").strip() or None,
            workspace_id=(workspace_id or "").strip() or None,
        )
        async with self._global_lock:
            await self._purge_expired_locked()
            self._runs[run_id] = rec
        return run_id

    async def get_run(self, run_id: str) -> AgentRunRecord | None:
        rid = str(run_id or "").strip()
        if not rid:
            return None
        async with self._global_lock:
            await self._purge_expired_locked()
            return self._runs.get(rid)

    async def append_event(self, run_id: str, data: str) -> int | None:
        rid = str(run_id or "").strip()
        if not rid:
            return None
        async with self._global_lock:
            rec = self._runs.get(rid)
            if rec is None:
                return None
        async with rec._lock:
            if rec.status != "running":
                return None
            seq = len(rec.events) + 1
            ev = BufferedSseEvent(seq=seq, data=str(data))
            rec.events.append(ev)
            if len(rec.events) > self._max_events:
                rec.events = rec.events[-self._max_events :]
                for i, item in enumerate(rec.events, start=1):
                    item.seq = i
            rec.updated_at = time.monotonic()
            subs = list(rec.subscribers)
        for q in subs:
            try:
                q.put_nowait(ev)
            except asyncio.QueueFull:
                pass
        return seq

    async def finish_run(self, run_id: str, *, status: RunStatus = "completed") -> None:
        rid = str(run_id or "").strip()
        if not rid:
            return
        async with self._global_lock:
            rec = self._runs.get(rid)
            if rec is None:
                return
        async with rec._lock:
            rec.status = status
            rec.updated_at = time.monotonic()
            subs = list(rec.subscribers)
        for q in subs:
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass

    async def subscribe(self, run_id: str) -> asyncio.Queue[BufferedSseEvent | None] | None:
        rec = await self.get_run(run_id)
        if rec is None:
            return None
        q: asyncio.Queue[BufferedSseEvent | None] = asyncio.Queue(maxsize=256)
        async with rec._lock:
            rec.subscribers.append(q)
        return q

    async def unsubscribe(self, run_id: str, q: asyncio.Queue[BufferedSseEvent | None]) -> None:
        rec = await self.get_run(run_id)
        if rec is None:
            return
        async with rec._lock:
            try:
                rec.subscribers.remove(q)
            except ValueError:
                pass

    async def events_after(self, run_id: str, after_seq: int) -> list[BufferedSseEvent]:
        rec = await self.get_run(run_id)
        if rec is None:
            return []
        async with rec._lock:
            return [e for e in rec.events if e.seq > after_seq]

    async def _purge_expired_locked(self) -> None:
        now = time.monotonic()
        expired = [rid for rid, rec in self._runs.items() if now - rec.updated_at > self._ttl]
        for rid in expired:
            del self._runs[rid]


_BUFFER: AgentRunBuffer | None = None


def get_agent_run_buffer(*, ttl_seconds: float | None = None) -> AgentRunBuffer:
    global _BUFFER
    if _BUFFER is None:
        ttl = float(ttl_seconds) if ttl_seconds is not None else _DEFAULT_TTL_S
        _BUFFER = AgentRunBuffer(ttl_seconds=ttl)
    return _BUFFER


def reset_agent_run_buffer_for_tests() -> None:
    """Clear singleton buffer (unit tests only)."""
    global _BUFFER
    _BUFFER = None


async def iter_buffered_run_sse(
    run_id: str,
    *,
    after_seq: int = 0,
) -> AsyncIterator[dict[str, str]]:
    """Replay buffered events then tail live until run completes."""
    buf = get_agent_run_buffer()
    rec = await buf.get_run(run_id)
    if rec is None:
        yield {
            "data": '{"type":"error","detail":"run_not_found","code":"agent_run_not_found"}',
        }
        return

    cursor = max(0, int(after_seq))
    for ev in await buf.events_after(run_id, cursor):
        cursor = ev.seq
        yield {"id": str(ev.seq), "data": ev.data}

    async with rec._lock:
        terminal = rec.status != "running"

    if terminal:
        if rec.status == "cancelled":
            yield {
                "data": json.dumps(
                    {
                        "type": "run_interrupted",
                        "code": "agent_run_cancelled",
                        "detail": "Agent run was interrupted before completion.",
                    }
                ),
            }
        elif rec.status == "failed":
            yield {
                "data": json.dumps(
                    {
                        "type": "error",
                        "code": "agent_run_failed",
                        "detail": "Agent run failed before completion.",
                    }
                ),
            }
        return

    q = await buf.subscribe(run_id)
    if q is None:
        return
    try:
        while True:
            try:
                item = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                rec2 = await buf.get_run(run_id)
                if rec2 is None or rec2.status != "running":
                    break
                continue
            if item is None:
                break
            if item.seq > cursor:
                cursor = item.seq
                yield {"id": str(item.seq), "data": item.data}
            rec_now = await buf.get_run(run_id)
            if rec_now is not None and rec_now.status != "running":
                for ev in await buf.events_after(run_id, cursor):
                    if ev.seq > cursor:
                        cursor = ev.seq
                        yield {"id": str(ev.seq), "data": ev.data}
                break
    finally:
        await buf.unsubscribe(run_id, q)


async def _buffer_inner_stream(
    run_id: str,
    inner: AsyncIterator[dict[str, str]],
    queue: asyncio.Queue[dict[str, str] | None],
) -> None:
    """Drain *inner* into run buffer and a forward queue (survives client disconnect)."""
    buf = get_agent_run_buffer()
    status: RunStatus = "completed"
    try:
        async for ev in inner:
            data = str(ev.get("data") or "")
            out = ev
            if data:
                seq = await buf.append_event(run_id, data)
                if seq is not None:
                    out = dict(ev)
                    out.setdefault("id", str(seq))
            try:
                queue.put_nowait(out)
            except asyncio.QueueFull:
                await queue.put(out)
    except asyncio.CancelledError:
        status = "cancelled"
    except Exception:
        status = "failed"
    finally:
        await buf.finish_run(run_id, status=status)
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            await queue.put(None)


async def wrap_stream_with_run_buffer(
    run_id: str,
    inner: AsyncIterator[dict[str, str]],
) -> AsyncIterator[dict[str, str]]:
    """Tee SSE payloads into the run buffer while forwarding to the client.

    Client disconnect cancels only this iterator; buffering continues in a background task
    so GET /runs/{run_id}/stream can replay and tail the same run.
    """
    queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue(maxsize=256)
    producer = asyncio.create_task(
        _buffer_inner_stream(run_id, inner, queue),
        name=f"agent-run-buffer-producer-{run_id}",
    )
    try:
        while True:
            ev = await queue.get()
            if ev is None:
                break
            yield ev
    except asyncio.CancelledError:
        raise
    finally:
        if producer.done():
            await producer
