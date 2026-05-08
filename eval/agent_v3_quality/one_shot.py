"""Subprocess entrypoint: run one agent question under a fixed ``SCIENCE_GRAPHRAG_AGENT_RUNTIME``.

Imports are intentionally deferred inside ``_run()`` so ``os.environ`` is applied first.

Usage (from repo root)::

    python -m eval.agent_v3_quality.one_shot <runtime> <request.json>

``request.json``::

    {"question": "...", "workspace_id": "ws-pilot-od|null", "max_tool_calls": 12}

Stdout: single JSON object with answer, citations, tool_trace, run_metadata, duration_ms, error.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from time import perf_counter
from typing import Any

# Imports in ``_run`` are deferred (see module docstring).
# pylint: disable=import-outside-toplevel

HEARTBEAT_ENV = "SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_HEARTBEAT_S"


def _heartbeat_seconds() -> float:
    raw = (os.environ.get(HEARTBEAT_ENV) or "").strip()
    if not raw:
        return 0.0
    try:
        val = float(raw)
    except ValueError:
        return 0.0
    return val if val > 0 else 0.0


def _run() -> dict[str, Any]:  # pylint: disable=too-many-locals
    if len(sys.argv) < 3:
        return {"error": "usage: python -m eval.agent_v3_quality.one_shot <runtime> <request.json>"}
    runtime = sys.argv[1].strip()
    req_path = Path(sys.argv[2])
    os.environ["SCIENCE_GRAPHRAG_AGENT_RUNTIME"] = runtime
    try:
        data = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"bad_request_json: {exc}"}
    question = str(data.get("question") or "").strip()
    ws = data.get("workspace_id")
    workspace_id = str(ws).strip() if ws not in (None, "", "null") else None
    max_tool_calls = int(data.get("max_tool_calls") or 12)
    started = perf_counter()
    heartbeat_s = _heartbeat_seconds()
    stop_heartbeat = threading.Event()

    def _heartbeat_loop() -> None:
        while not stop_heartbeat.wait(heartbeat_s):
            elapsed = perf_counter() - started
            print(
                f"[agent_v3_quality.one_shot] runtime={runtime} elapsed_s={elapsed:.1f}",
                file=sys.stderr,
                flush=True,
            )

    heartbeat_thread: threading.Thread | None = None
    if heartbeat_s > 0:
        heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            name="agent_v3_quality_one_shot_heartbeat",
            daemon=True,
        )
        heartbeat_thread.start()
    try:
        # Deferred imports so subprocess children pick up env overrides before graph deps load.
        from science_graphrag.agent.runtime import build_agent
        from science_graphrag.api.deps import init_store_registry
        from science_graphrag.config import get_settings

        settings = get_settings()
        stores = init_store_registry(settings)
        agent = build_agent(settings=settings, stores=stores)
        out = agent.run(
            question=question,
            workspace_id=workspace_id,
            max_tool_calls=max_tool_calls,
        )
        duration_ms = int((perf_counter() - started) * 1000)
        return {
            "answer": out.answer,
            "citations": list(out.citations or []),
            "tool_trace": list(out.tool_trace or []),
            "routing_log": list(out.routing_log or []),
            "warnings": list(getattr(out, "warnings", None) or []),
            "run_metadata": dict(getattr(out, "run_metadata", None) or {}),
            "duration_ms": duration_ms,
            "agent_runtime_effective": str(settings.agent_runtime),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "error": f"{type(exc).__name__}: {exc}",
            "duration_ms": int((perf_counter() - started) * 1000),
        }
    finally:
        if heartbeat_thread is not None:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=0.1)


def main() -> None:
    """Emit one JSON object on stdout for ``python -m eval.agent_v3_quality.one_shot``."""

    report = _run()
    sys.stdout.write(json.dumps(report, ensure_ascii=False, default=str))
    sys.stdout.flush()
    if report.get("error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
