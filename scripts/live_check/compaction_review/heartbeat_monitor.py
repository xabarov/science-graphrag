"""Stderr progress lines for compaction turn review (operator visibility)."""

from __future__ import annotations

import sys
from typing import Any


def log_turn_start(
    *,
    turn_idx: int,
    attempt: int,
    thread_id: str,
    hb_sec: float,
    mode: str,
) -> None:
    """Emit ``turn_start`` line before blocking HTTP work."""
    print(
        (
            f"[compaction-review] turn_start turn={turn_idx} attempt={attempt} "
            f"thread_id={thread_id} hb_sec={hb_sec} mode={mode}"
        ),
        file=sys.stderr,
        flush=True,
    )


def log_turn_done(
    *,
    turn_idx: int,
    elapsed_ms: int,
    kinds: list[Any],
    side_ratio: Any,
    paper_restored: Any,
) -> None:
    """Emit ``turn_done`` line after a successful turn response."""
    print(
        (
            f"[compaction-review] turn_done turn={turn_idx} elapsed_ms={elapsed_ms} "
            f"kinds={','.join(str(k) for k in kinds)} "
            f"side_ratio={side_ratio!r} "
            f"paper_restored={paper_restored!r}"
        ),
        file=sys.stderr,
        flush=True,
    )


__all__ = ["log_turn_done", "log_turn_start"]
