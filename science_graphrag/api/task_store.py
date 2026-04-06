"""In-memory task store for benchmark runs.

This module provides a minimal background execution layer for the UI:
- create a run (set of case_ids)
- execute cases concurrently in a ThreadPoolExecutor
- expose run status/progress and per-case results (metrics + predicted + gold)

Note: cancellation is "best-effort" (can't interrupt a running case extraction).
"""

from __future__ import annotations

import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from eval.layer1.runner import run_case


class RunCancelledError(RuntimeError):
    """Raised when a run is cancelled before starting a case."""


class RunStatus(str):
    """String constants for run lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    status: str = RunStatus.QUEUED
    created_at: str = field(default_factory=_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    cancel_requested: bool = False
    error_message: str | None = None
    cases: dict[str, RunCaseRecord] = field(default_factory=dict)

    def progress_counts(self) -> dict[str, int]:
        """Return total/completed counters for the UI progress bar."""
        total = len(self.case_ids)
        completed = len(self.cases)
        # "Completed" means: finished successfully or with error/cancelled.
        return {"total": total, "completed": completed}


def _extract_case_f1_for_averages(case_result: dict[str, Any]) -> dict[str, float]:
    """Best-effort extraction of commonly used f1 values for UI summary."""
    metrics = (case_result or {}).get("metrics") or {}
    authorships = metrics.get("authorships") or {}
    references = metrics.get("references") or {}

    # Layer-1 metrics: authorships.names_f1, references.sample_arxiv_f1, references.sample_doi_f1.
    names_f1 = float(authorships.get("names_f1") or 0.0)
    sample_arxiv_f1 = float(references.get("sample_arxiv_f1") or 0.0)
    sample_doi_f1 = float(references.get("sample_doi_f1") or 0.0)
    return {
        "names_f1": names_f1,
        "sample_arxiv_f1": sample_arxiv_f1,
        "sample_doi_f1": sample_doi_f1,
    }


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


class BenchmarkTaskStore:
    """In-memory storage and background runner for benchmark runs."""

    def __init__(self, *, max_workers: int = 2) -> None:
        """Initialize the executor + the in-memory run registry."""
        self._runs: dict[str, RunRecord] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def create_run(self, *, case_ids: list[str], label: str | None = None) -> str:
        """Create a run record and start executing it immediately."""
        run_id = str(uuid.uuid4())
        rec = RunRecord(run_id=run_id, label=label, case_ids=list(case_ids))
        with self._lock:
            self._runs[run_id] = rec
        self.start_run(run_id)
        return run_id

    def start_run(self, run_id: str) -> None:
        """Submit all case jobs for the run to the executor."""
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return
            rec.status = RunStatus.RUNNING
            rec.started_at = _now_iso()

        for case_id in rec.case_ids:
            fut = self._executor.submit(self._run_one_case, run_id, case_id)
            fut.add_done_callback(
                lambda f, rid=run_id, cid=case_id: self._on_case_finished(rid, cid, f)
            )

    def cancel_run(self, run_id: str) -> bool:
        """Request best-effort cancellation for all not-yet-started cases."""
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return False
            rec.cancel_requested = True
            # Keep status as running until callbacks finish.
            if rec.status == RunStatus.QUEUED:
                rec.status = RunStatus.CANCELLED
                rec.completed_at = _now_iso()
            return True

    def delete_run(self, run_id: str) -> bool:
        """Remove run record from memory (does not stop running futures)."""
        with self._lock:
            return self._runs.pop(run_id, None) is not None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a full run detail (metrics/predicted/gold per case)."""
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return None
            return self._run_to_dict(rec)

    def list_runs_summary(self) -> list[dict[str, Any]]:
        """List run summaries for the runs table."""
        with self._lock:
            records = list(self._runs.values())
            return [self._run_summary_to_dict(r) for r in records]

    def _run_root_fixtures_layer1(self) -> Path:
        """Return path to layer-1 benchmark fixtures root."""
        # science_graphrag/api/task_store.py -> .../science_graphrag/
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "tests" / "fixtures" / "benchmarks" / "layer1"

    def _run_one_case(self, run_id: str, case_id: str) -> dict[str, Any]:
        """Execute one benchmark case and return the run_case payload."""
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                raise KeyError(f"run_not_found:{run_id}")
            if rec.cancel_requested:
                raise RunCancelledError("cancel_requested")

        fixture_dir = self._run_root_fixtures_layer1() / case_id
        if not fixture_dir.is_dir():
            raise FileNotFoundError(f"fixture_dir_not_found:{fixture_dir}")

        return run_case(fixture_dir)

    def _on_case_finished(self, run_id: str, case_id: str, fut: Future[dict[str, Any]]) -> None:
        """Executor callback: store per-case result and update terminal status."""
        # Callback may run in executor thread; keep lock scope minimal.
        status: str
        result: dict[str, Any] | None = None
        error_message: str | None = None
        try:
            result = fut.result()
            status = "ok"
        except RunCancelledError as e:
            status = "cancelled"
            error_message = str(e)
        except Exception as e:  # noqa: BLE001
            status = "failed"
            error_message = f"{type(e).__name__}: {e}"

        finished_at = _now_iso()

        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return

            rec.cases[case_id] = RunCaseRecord(
                case_id=case_id,
                status=status,
                result=result,
                error_message=error_message,
                finished_at=finished_at,
            )

            counts = rec.progress_counts()
            if counts["completed"] >= counts["total"]:
                # Decide terminal status.
                rec.completed_at = _now_iso()
                if rec.cancel_requested and all(
                    cr.status == "cancelled" for cr in rec.cases.values()
                ):
                    rec.status = RunStatus.CANCELLED
                elif any(cr.status == "failed" for cr in rec.cases.values()):
                    rec.status = RunStatus.FAILED
                else:
                    # Some cases can be cancelled; still treat as completed if no failures.
                    rec.status = RunStatus.COMPLETED

    def _run_to_dict(self, rec: RunRecord) -> dict[str, Any]:
        """Serialize a full run (progress + summaries + all case results)."""
        # Keep response stable for UI.
        counts = rec.progress_counts()
        # "cases" as array for deterministic ordering by case_ids.
        cases_out: list[dict[str, Any]] = []
        for cid in rec.case_ids:
            if cid in rec.cases:
                cases_out.append(rec.cases[cid].to_dict())
            else:
                # UI can show "pending" cards if desired.
                cases_out.append({"case_id": cid, "status": "pending"})

        # Averages over successfully executed cases only.
        ok_results = [c.result for c in rec.cases.values() if c.status == "ok" and c.result]
        f1_names = [_extract_case_f1_for_averages(r)["names_f1"] for r in ok_results]
        f1_arxiv = [_extract_case_f1_for_averages(r)["sample_arxiv_f1"] for r in ok_results]
        f1_doi = [_extract_case_f1_for_averages(r)["sample_doi_f1"] for r in ok_results]

        avg_f1_names = _mean(f1_names)
        avg_f1_arxiv = _mean(f1_arxiv)
        avg_f1_doi = _mean(f1_doi)

        return {
            "run_id": rec.run_id,
            "label": rec.label,
            "status": rec.status,
            "created_at": rec.created_at,
            "started_at": rec.started_at,
            "completed_at": rec.completed_at,
            "error_message": rec.error_message,
            "progress": {
                "total": counts["total"],
                "completed": counts["completed"],
                "percent": (
                    (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
                ),
            },
            "summary": {
                "avg_names_f1": avg_f1_names,
                "avg_sample_arxiv_f1": avg_f1_arxiv,
                "avg_sample_doi_f1": avg_f1_doi,
                "pass_count": len(
                    [
                        1
                        for c in rec.cases.values()
                        if c.status == "ok"
                        and (c.result.get("metrics", {}).get("contract", {}).get("passed") is True)
                    ]
                ),
                "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
                "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
            },
            "cases": cases_out,
        }

    def _run_summary_to_dict(self, rec: RunRecord) -> dict[str, Any]:
        """Serialize a compact run row for the runs list."""
        # Summary for runs list.
        counts = rec.progress_counts()
        return {
            "run_id": rec.run_id,
            "label": rec.label,
            "status": rec.status,
            "created_at": rec.created_at,
            "started_at": rec.started_at,
            "completed_at": rec.completed_at,
            "progress": {
                "total": counts["total"],
                "completed": counts["completed"],
                "percent": (
                    (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
                ),
            },
            # Compute averages only over finished ok cases.
            "summary": {
                "avg_names_f1": _mean(
                    [
                        _extract_case_f1_for_averages(c.result)["names_f1"]
                        for c in rec.cases.values()
                        if c.status == "ok" and c.result
                    ]
                ),
                "avg_sample_arxiv_f1": _mean(
                    [
                        _extract_case_f1_for_averages(c.result)["sample_arxiv_f1"]
                        for c in rec.cases.values()
                        if c.status == "ok" and c.result
                    ]
                ),
                "avg_sample_doi_f1": _mean(
                    [
                        _extract_case_f1_for_averages(c.result)["sample_doi_f1"]
                        for c in rec.cases.values()
                        if c.status == "ok" and c.result
                    ]
                ),
                "pass_count": len(
                    [
                        1
                        for c in rec.cases.values()
                        if c.status == "ok"
                        and c.result
                        and c.result.get("metrics", {}).get("contract", {}).get("passed") is True
                    ]
                ),
                "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
                "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
            },
        }


# A process-level singleton used by the API router.
task_store = BenchmarkTaskStore(max_workers=2)
