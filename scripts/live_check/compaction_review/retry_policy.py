"""Compaction review: failure classification and stop semantics (R3 / W3)."""

from __future__ import annotations

import sys


def compaction_review_stop_outcome(
    *,
    failure_reason: str | None,
    verdict_status: str,
) -> tuple[str, bool]:
    """Machine-readable end state for compaction review JSON (W3 / R3).

    Returns ``(stop_reason, fail_fast)``:
    - ``stopped_on_turn_failure`` + ``fail_fast=True`` when a turn hard-stopped the lane;
    - ``completed_turns_verdict_fail`` when all turns ran but compaction verdict failed;
    - ``completed`` on pass.
    """
    if failure_reason:
        return "stopped_on_turn_failure", True
    if verdict_status == "fail":
        return "completed_turns_verdict_fail", False
    return "completed", False


def classify_turn_failure(
    *,
    mode: str,
    failure_kind_raw: str,
    turn_idx: int,
    elapsed_ms: int,
    silent_hang_threshold_s: float,
) -> tuple[str, str]:
    """Map transport failures to deterministic failure_kind/failure_reason."""
    if failure_kind_raw in {"http_read_timeout", "http_timeout"}:
        if mode == "focused_long_thread" and elapsed_ms >= int(silent_hang_threshold_s * 1000):
            return "silent_hang", f"silent_hang_turn_{turn_idx}"
        return "http_timeout", f"http_timeout_turn_{turn_idx}"
    if failure_kind_raw == "http_error":
        return "http_error", f"http_error_turn_{turn_idx}"
    return "unknown_error", f"unknown_error_turn_{turn_idx}"


def log_turn_fail_stderr(*, turn_idx: int, failure_reason: str, elapsed_ms: int) -> None:
    """Emit a single stderr line after a turn hard-stops (operator-facing)."""
    print(
        f"[compaction-review] turn_fail turn={turn_idx} "
        f"reason={failure_reason} elapsed_ms={elapsed_ms}",
        file=sys.stderr,
        flush=True,
    )


__all__ = [
    "classify_turn_failure",
    "compaction_review_stop_outcome",
    "log_turn_fail_stderr",
]
