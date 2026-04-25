from __future__ import annotations

import asyncio
import json
import threading
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict

import redis
import redis.asyncio as aioredis
from sqlalchemy import delete, func, select

from science_graphrag.config import get_settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import IngestJobEventOrm

_SENTINEL = object()


class IngestEvent(TypedDict):
    job_id: str
    kind: str
    payload: dict[str, Any]


class IngestEventBus:
    def __init__(self) -> None:
        self._session_factory = None
        self._db_ready = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._settings = get_settings()
        self._channel_prefix = "ingest:events"
        self._redis_sync = redis.Redis.from_url(
            self._settings.redis_url,
            decode_responses=True,
        )
        self._redis_async = aioredis.from_url(
            self._settings.redis_url,
            decode_responses=True,
        )
        self._subscribers: dict[str, set[asyncio.Queue[Any]]] = defaultdict(set)
        self._memory_events: dict[str, list[tuple[int, IngestEvent, datetime]]] = defaultdict(list)
        self._memory_seq: dict[str, int] = defaultdict(int)

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        with self._loop_lock:
            self._loop = loop

    def publish_threadsafe(self, event: IngestEvent) -> int:
        seq = self._persist_event(event)
        envelope = json.dumps({"seq": seq, "event": event}, ensure_ascii=True, default=str)
        published = False
        try:
            self._redis_sync.publish(self._channel(event["job_id"]), envelope)
            published = True
        except Exception:
            published = False
        with self._loop_lock:
            loop = self._loop
        if published or loop is None:
            return seq
        asyncio.run_coroutine_threadsafe(self._fanout(seq, event), loop)
        return seq

    def replay_from(self, job_id: str, last_seq: int) -> list[tuple[int, IngestEvent]]:
        key = str(job_id).strip()
        if self._ensure_db():
            with self._session_factory() as session:
                rows = (
                    session.execute(
                        select(IngestJobEventOrm)
                        .where(
                            IngestJobEventOrm.job_id == key,
                            IngestJobEventOrm.seq > int(last_seq),
                        )
                        .order_by(IngestJobEventOrm.seq.asc())
                    )
                    .scalars()
                    .all()
                )
                out: list[tuple[int, IngestEvent]] = []
                for row in rows:
                    payload: dict[str, Any] = {}
                    raw = (row.payload_json or "").strip()
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            if isinstance(parsed, dict):
                                payload = parsed
                        except Exception:
                            payload = {}
                    out.append(
                        (
                            int(row.seq),
                            {"job_id": row.job_id, "kind": row.kind, "payload": payload},
                        )
                    )
                return out
        return [
            (seq, event)
            for seq, event, _ in self._memory_events.get(key, [])
            if seq > int(last_seq)
        ]

    async def subscribe(self, job_id: str) -> AsyncIterator[tuple[int, IngestEvent]]:
        key = str(job_id).strip()
        channel = self._channel(key)
        pubsub = self._redis_async.pubsub()
        subscribed = False
        try:
            await pubsub.subscribe(channel)
            subscribed = True
        except Exception:
            subscribed = False

        if subscribed:
            try:
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    raw = str(message.get("data") or "").strip()
                    if not raw:
                        continue
                    try:
                        parsed = json.loads(raw)
                        seq = int(parsed["seq"])
                        event = parsed["event"]
                        if isinstance(event, dict):
                            yield seq, event
                    except Exception:
                        continue
            finally:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            return

        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=256)
        self._subscribers[key].add(queue)
        try:
            while True:
                item = await queue.get()
                if item is _SENTINEL:
                    return
                yield item
        finally:
            self._subscribers[key].discard(queue)
            if not self._subscribers[key]:
                self._subscribers.pop(key, None)

    def _channel(self, job_id: str) -> str:
        return f"{self._channel_prefix}:{str(job_id).strip()}"

    def cleanup_old_events(self, *, ttl_hours: int = 24) -> None:
        cutoff = datetime.now(UTC) - timedelta(hours=max(1, ttl_hours))
        if self._ensure_db():
            with self._session_factory() as session:
                session.execute(
                    delete(IngestJobEventOrm).where(IngestJobEventOrm.created_at < cutoff),
                )
                session.commit()
            return
        for key in list(self._memory_events.keys()):
            rows = [row for row in self._memory_events.get(key, []) if row[2] >= cutoff]
            if rows:
                self._memory_events[key] = rows
                self._memory_seq[key] = rows[-1][0]
            else:
                self._memory_events.pop(key, None)
                self._memory_seq.pop(key, None)

    def _persist_event(self, event: IngestEvent) -> int:
        key = str(event["job_id"]).strip()
        with self._write_lock:
            if self._ensure_db():
                with self._session_factory() as session:
                    next_seq = (
                        session.execute(
                            select(func.max(IngestJobEventOrm.seq)).where(
                                IngestJobEventOrm.job_id == key,
                            )
                        ).scalar_one()
                        or 0
                    ) + 1
                    row = IngestJobEventOrm(
                        job_id=key,
                        seq=int(next_seq),
                        kind=str(event["kind"]).strip(),
                        payload_json=json.dumps(
                            event.get("payload") or {}, ensure_ascii=True, default=str
                        ),
                    )
                    session.add(row)
                    session.commit()
                    return int(next_seq)
            next_seq = int(self._memory_seq.get(key, 0)) + 1
            self._memory_seq[key] = next_seq
            self._memory_events[key].append((next_seq, event, datetime.now(UTC)))
            return next_seq

    def _ensure_db(self) -> bool:
        if self._db_ready and self._session_factory is not None:
            return True
        try:
            settings = get_settings()
            engine = get_engine(settings.database_url)
            init_db(engine)
            self._session_factory = session_factory(engine)
            self._db_ready = True
            return True
        except Exception:
            self._db_ready = False
            self._session_factory = None
            return False

    async def _fanout(self, seq: int, event: IngestEvent) -> None:
        key = str(event["job_id"]).strip()
        subscribers = list(self._subscribers.get(key, set()))
        for queue in subscribers:
            await queue.put((seq, event))
            if event["kind"] == "terminal":
                await queue.put(_SENTINEL)


BUS = IngestEventBus()
