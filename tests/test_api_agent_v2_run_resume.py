"""Agent v2 SSE run buffer + resume stream endpoint."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from science_graphrag.api.agent_v2_modules.agent_run_buffer import (
    get_agent_run_buffer,
    reset_agent_run_buffer_for_tests,
)
from science_graphrag.api.main import app


@pytest.fixture(autouse=True)
def _reset_buffer() -> None:
    reset_agent_run_buffer_for_tests()
    yield
    reset_agent_run_buffer_for_tests()


def test_run_buffer_append_and_replay() -> None:
    async def _run() -> None:
        buf = get_agent_run_buffer(ttl_seconds=120)
        run_id = await buf.create_run(thread_id="sess-1", workspace_id="ws-1")
        s1 = await buf.append_event(run_id, json.dumps({"type": "product_step", "code": "a"}))
        s2 = await buf.append_event(run_id, json.dumps({"type": "product_step", "code": "b"}))
        assert s1 == 1
        assert s2 == 2
        replay = await buf.events_after(run_id, 1)
        assert len(replay) == 1
        assert replay[0].seq == 2
        await buf.finish_run(run_id, status="completed")

    asyncio.run(_run())


def test_resume_stream_endpoint_replays_events() -> None:
    async def _seed() -> str:
        buf = get_agent_run_buffer(ttl_seconds=120)
        run_id = await buf.create_run(thread_id="t1", workspace_id="ws")
        await buf.append_event(run_id, json.dumps({"type": "product_step", "code": "x"}))
        await buf.append_event(
            run_id,
            json.dumps({"type": "final_answer", "answer": "ok", "citations": []}),
        )
        await buf.finish_run(run_id, status="completed")
        return run_id

    run_id = asyncio.run(_seed())

    client = TestClient(app)
    with client.stream(
        "GET",
        f"/v2/agent/query/runs/{run_id}/stream",
        params={"after_seq": 0},
        headers={"Accept": "text/event-stream"},
    ) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    assert "product_step" in body
    assert "final_answer" in body


def test_wrap_stream_survives_client_disconnect() -> None:
    """Background producer keeps buffering after the SSE consumer is closed."""

    async def _run() -> None:
        from science_graphrag.api.agent_v2_modules.agent_run_buffer import (
            get_agent_run_buffer,
            wrap_stream_with_run_buffer,
        )

        buf = get_agent_run_buffer(ttl_seconds=120)
        run_id = await buf.create_run(thread_id="sess-disc", workspace_id="ws-disc")
        gate = asyncio.Event()

        async def inner():
            yield {"data": json.dumps({"type": "product_step", "code": "x"})}
            await gate.wait()
            yield {
                "data": json.dumps(
                    {"type": "final_answer", "answer": "ok", "citations": []},
                ),
            }

        gen = wrap_stream_with_run_buffer(run_id, inner())
        first = await gen.__anext__()
        assert "product_step" in first.get("data", "")
        await gen.aclose()
        gate.set()
        for _ in range(50):
            rec = await buf.get_run(run_id)
            if rec is not None and rec.status != "running":
                break
            await asyncio.sleep(0.02)
        rec = await buf.get_run(run_id)
        assert rec is not None
        assert rec.status == "completed"
        replay = await buf.events_after(run_id, 0)
        assert any("final_answer" in e.data for e in replay)

    asyncio.run(_run())


def test_resume_stream_cancelled_emits_run_interrupted() -> None:
    async def _seed() -> str:
        buf = get_agent_run_buffer(ttl_seconds=120)
        run_id = await buf.create_run(thread_id="t1", workspace_id="ws")
        await buf.append_event(run_id, json.dumps({"type": "product_step", "code": "x"}))
        await buf.finish_run(run_id, status="cancelled")
        return run_id

    run_id = asyncio.run(_seed())
    client = TestClient(app)
    with client.stream(
        "GET",
        f"/v2/agent/query/runs/{run_id}/stream",
        params={"after_seq": 0},
        headers={"Accept": "text/event-stream"},
    ) as res:
        assert res.status_code == 200
        body = "".join(res.iter_text())
    assert "run_interrupted" in body


def test_resume_stream_not_found() -> None:
    client = TestClient(app)
    res = client.get(
        "/v2/agent/query/runs/run-missing/stream",
        params={"after_seq": 0},
        headers={"Accept": "text/event-stream"},
    )
    assert res.status_code == 404
