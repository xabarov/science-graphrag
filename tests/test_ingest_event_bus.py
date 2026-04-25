from __future__ import annotations

import asyncio
import uuid
from typing import Any

from science_graphrag.api.ingest_event_bus import IngestEventBus


def test_ingest_event_bus_fanout_and_replay() -> None:
    async def _run() -> None:
        bus = IngestEventBus()
        bus.attach_loop(asyncio.get_running_loop())
        job_id = str(uuid.uuid4())
        received_a: list[tuple[int, dict[str, Any]]] = []
        received_b: list[tuple[int, dict[str, Any]]] = []

        async def _collect(target: list[tuple[int, dict[str, Any]]]) -> None:
            async for seq, event in bus.subscribe(job_id):
                target.append((seq, event))
                if event["kind"] == "terminal":
                    break

        task_a = asyncio.create_task(_collect(received_a))
        task_b = asyncio.create_task(_collect(received_b))
        await asyncio.sleep(0.01)

        first_seq = bus.publish_threadsafe(
            {
                "job_id": job_id,
                "kind": "stage_started",
                "payload": {"job_id": job_id, "stage": "parse_pdf", "status": "running"},
            }
        )
        second_seq = bus.publish_threadsafe(
            {
                "job_id": job_id,
                "kind": "terminal",
                "payload": {"job_id": job_id, "status": "completed"},
            }
        )

        await asyncio.wait_for(asyncio.gather(task_a, task_b), timeout=2.0)

        assert first_seq >= 1
        assert second_seq == first_seq + 1
        assert [row[1]["kind"] for row in received_a] == ["stage_started", "terminal"]
        assert [row[1]["kind"] for row in received_b] == ["stage_started", "terminal"]

        replay = bus.replay_from(job_id, 0)
        assert len(replay) >= 2
        assert replay[0][1]["kind"] == "stage_started"
        assert replay[-1][1]["kind"] == "terminal"

    asyncio.run(_run())
