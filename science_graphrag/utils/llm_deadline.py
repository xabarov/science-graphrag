"""Monotonic deadlines for LLM operation budgets (Phase 1 timeout enforcement)."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class MonotonicDeadline:
    """Wall-clock-jump-safe deadline using ``time.monotonic()``."""

    _end: float

    @staticmethod
    def from_budget_seconds(seconds: float | None) -> MonotonicDeadline | None:
        """Return ``None`` when ``seconds`` is missing or non-positive."""

        if seconds is None:
            return None
        s = float(seconds)
        if s <= 0:
            return None
        return MonotonicDeadline(_end=time.monotonic() + s)

    def remaining(self) -> float:
        """Seconds left before the deadline; ``0.0`` when elapsed or past."""

        return max(0.0, self._end - time.monotonic())

    def exhausted(self) -> bool:
        """True when no budget remains for further work or sleeps."""

        return self.remaining() <= 0.0
