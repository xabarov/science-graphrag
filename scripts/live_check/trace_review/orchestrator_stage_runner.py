"""Long-running stage execution with stderr heartbeat + diagnostics rows."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Any


def execute_trace_stage(
    exec_stages: list[dict[str, Any]],
    name: str,
    fn: Callable[[], Any],
    *,
    heartbeat_interval_s: float,
) -> Any:
    """Run a long stage with stderr heartbeat + JSON ``execution_diagnostics`` rows."""
    from agent_trace_review_heartbeat import (  # pylint: disable=import-outside-toplevel,import-error
        StageHeartbeat,
        record_stage,
    )

    hb = StageHeartbeat(name, interval_s=heartbeat_interval_s)
    print(f"[trace-review] stage_start {name}", file=sys.stderr, flush=True)
    hb.start()
    t0 = time.perf_counter()
    ok = False
    detail: str | None = None
    try:
        out = fn()
        ok = True
        return out
    except Exception as exc:  # noqa: BLE001
        detail = f"{type(exc).__name__}:{exc}"[:2000]
        raise
    finally:
        hb.stop()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        record_stage(
            exec_stages,
            stage=name,
            elapsed_ms=elapsed_ms,
            ok=ok,
            detail=detail if not ok else None,
        )
        print(
            f"[trace-review] stage_done {name} elapsed_ms={elapsed_ms:.0f} ok={ok}",
            file=sys.stderr,
            flush=True,
        )
