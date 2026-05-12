"""Periodic stderr heartbeat for long-running ``agent_trace_review`` stages."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any


class StageHeartbeat:
    """Background stderr heartbeat for a named stage."""

    def __init__(self, stage: str, *, interval_s: float = 60.0) -> None:
        self._stage = str(stage or "unknown")
        self._interval_s = max(5.0, float(interval_s))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._started = time.perf_counter()

    def start(self) -> None:
        """Start the background heartbeat thread."""

        def _loop() -> None:
            while not self._stop.wait(self._interval_s):
                elapsed = time.perf_counter() - self._started
                print(
                    f"[trace-review] heartbeat stage={self._stage} elapsed_s={elapsed:.1f}",
                    file=sys.stderr,
                    flush=True,
                )

        self._thread = threading.Thread(
            target=_loop, name=f"trace-review-heartbeat-{self._stage}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop heartbeat and join the thread."""

        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=min(2.0, self._interval_s + 1.0))
            self._thread = None


def record_stage(
    stages: list[dict[str, Any]],
    *,
    stage: str,
    elapsed_ms: float,
    ok: bool,
    detail: str | None = None,
) -> None:
    """Append one row to ``execution_diagnostics.stages`` in the trace-review JSON."""

    row: dict[str, Any] = {
        "stage": stage,
        "elapsed_ms": round(float(elapsed_ms), 3),
        "ok": bool(ok),
    }
    if detail:
        row["detail"] = detail[:2000]
    stages.append(row)
