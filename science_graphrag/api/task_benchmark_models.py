"""Domain models and constants for benchmark background runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class RunCancelledError(RuntimeError):
    """Raised when a run is cancelled before starting a case."""


class RunPayloadTooLargeError(RuntimeError):
    """Full run JSON is refused (API returns 413); use summary + paginated cases or CLI."""


class RunStatus(str):
    """String constants for run lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def now_iso() -> str:
    """UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


# Above this count, ``get_run_summary`` omits ``cases``; use ``get_run_cases_page``.
SUMMARY_CASES_INLINE_MAX = 100

# Full ``GET .../runs/{run_id}`` guardrails (avoid multi-GB JSON in API memory).
FULL_RUN_MAX_CASE_IDS = 2000
FULL_RUN_MAX_FILE_BYTES = 50 * 1024 * 1024
FULL_RUN_BLOCK_DETAIL = "run_payload_too_large_use_cases_api"


@dataclass
class RunCaseRecord:
    """Per-case record inside a run."""

    case_id: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "case_id": self.case_id,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "finished_at": self.finished_at,
        }


@dataclass
class RunRecord:
    """Run record: a set of case executions with aggregated progress."""

    run_id: str
    label: str | None
    case_ids: list[str]
    benchmark_family: str = "layer1"
    status: str = RunStatus.QUEUED
    created_at: str = field(default_factory=now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    cancel_requested: bool = False
    error_message: str | None = None
    run_config: dict[str, Any] = field(default_factory=dict)
    cases: dict[str, RunCaseRecord] = field(default_factory=dict)

    def progress_counts(self) -> dict[str, int]:
        """Return total/completed counters for the UI progress bar."""
        total = len(self.case_ids)
        completed = len(self.cases)
        return {"total": total, "completed": completed}
