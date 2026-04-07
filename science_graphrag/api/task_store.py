"""In-memory task store for benchmark runs.

This module provides a minimal background execution layer for the UI:
- create a run (set of case_ids)
- execute cases concurrently in a ThreadPoolExecutor
- expose run status/progress and per-case results (metrics + predicted + gold)

Note: cancellation is "best-effort" (can't interrupt a running case extraction).
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from eval.layer1.runner import run_case as run_layer1_case
from eval.layer2.runner import run_case as run_layer2_case
from science_graphrag.api.benchmark_profiles import (
    build_settings_for_run,
    prepare_run_config,
    public_run_config,
)


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Above this count, ``get_run_summary`` omits ``cases``; use ``get_run_cases_page``.
_SUMMARY_CASES_INLINE_MAX = 100

# Full ``GET .../runs/{run_id}`` guardrails (avoid multi-GB JSON in API memory).
_FULL_RUN_MAX_CASE_IDS = 2000
_FULL_RUN_MAX_FILE_BYTES = 50 * 1024 * 1024
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
    created_at: str = field(default_factory=_now_iso)
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


def _case_contract_passed(result: dict[str, Any] | None) -> bool:
    """Layer-1 uses metrics.contract.passed; layer-2 uses metrics.passed."""
    if not result:
        return False
    metrics = result.get("metrics") or {}
    contract = metrics.get("contract") or {}
    if contract.get("passed") is True:
        return True
    if metrics.get("passed") is True:
        return True
    return False


def _case_result_summary_static(case_record: RunCaseRecord) -> dict[str, Any]:
    """Per-case summary for UI tables (same shape as BenchmarkTaskStore._case_result_summary)."""
    result = case_record.result or {}
    metrics = result.get("metrics") or {}
    failed_checks = [
        name
        for name, passed in (metrics.get("contract", {}).get("checks") or {}).items()
        if passed is False
    ]
    out: dict[str, Any] = {
        "passed": _case_contract_passed(result),
        "failed_checks": failed_checks,
        "names_f1": metrics.get("authorships", {}).get("names_f1"),
        "sample_arxiv_f1": metrics.get("references", {}).get("sample_arxiv_f1"),
        "sample_doi_f1": metrics.get("references", {}).get("sample_doi_f1"),
        "precision_methods": metrics.get("precision_methods"),
        "precision_datasets": metrics.get("precision_datasets"),
    }
    if metrics.get("precision_methods") is not None:
        out["layer2_recall_ratio"] = _layer2_recall_ratio(metrics)
    return out


def _layer2_recall_ratio(metrics: dict[str, Any]) -> float:
    """Single scalar for summary: mean of method and dataset recall ratios."""
    m_num = float(metrics.get("recall_methods_num") or 0)
    m_den = float(metrics.get("recall_methods_denom") or 0) or 1.0
    d_num = float(metrics.get("recall_datasets_num") or 0)
    d_den = float(metrics.get("recall_datasets_denom") or 0) or 1.0
    return float((m_num / m_den + d_num / d_den) / 2.0)


class BenchmarkTaskStore:
    """In-memory storage and background runner for benchmark runs."""

    def __init__(
        self,
        *,
        max_workers: int = 2,
        history_dir: Path | None = None,
        layer1_runner=run_layer1_case,
        layer2_runner=run_layer2_case,
    ) -> None:
        """Initialize the executor + the in-memory run registry."""
        self._runs: dict[str, RunRecord] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._history_dir_override = history_dir
        self._layer1_runner = layer1_runner
        self._layer2_runner = layer2_runner
        self._load_persisted_runs()

    def create_run(
        self,
        *,
        case_ids: list[str],
        label: str | None = None,
        benchmark_family: str = "layer1",
        run_config: dict[str, Any] | None = None,
    ) -> str:
        """Create a run record and start executing it immediately."""
        run_id = str(uuid.uuid4())
        fam = (benchmark_family or "layer1").strip().lower()
        if fam not in ("layer1", "layer2"):
            fam = "layer1"
        prepared_run_config = prepare_run_config(
            benchmark_family=fam,
            requested_config=run_config,
        )
        rec = RunRecord(
            run_id=run_id,
            label=label,
            case_ids=list(case_ids),
            benchmark_family=fam,
            run_config=prepared_run_config,
        )
        with self._lock:
            self._runs[run_id] = rec
            self._persist_run_snapshot(rec)
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
            self._persist_run_snapshot(rec)

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
            deleted = self._runs.pop(run_id, None) is not None
        if deleted:
            self._delete_persisted_run(run_id)
        return deleted

    def find_last_run_hint_for_case(
        self,
        case_id: str,
        benchmark_family: str,
        *,
        max_files: int = 200,
    ) -> dict[str, Any] | None:
        """Scan recent persisted run JSON files for the latest completed row for ``case_id``.

        Looks under :meth:`_history_dir` and :meth:`_legacy_history_dir`, newest files first
        (by filesystem mtime), up to ``max_files`` files. Match requires ``benchmark_family``
        and per-case ``case_id`` equality (string compare).
        """
        cid = (case_id or "").strip()
        if not cid:
            return None
        fam = (benchmark_family or "layer1").strip().lower()
        dirs: list[Path] = [self._history_dir()]
        legacy = self._legacy_history_dir()
        if legacy.resolve() != dirs[0].resolve():
            dirs.append(legacy)
        paths: list[Path] = []
        for d in dirs:
            if not d.is_dir():
                continue
            paths.extend(p for p in d.glob("*.json") if p.is_file())
        try:
            paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            paths.sort(key=lambda p: str(p), reverse=True)
        paths = paths[: max(0, max_files)]
        for path in paths:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                continue
            if payload.get("status") != RunStatus.COMPLETED:
                continue
            pfam = (payload.get("benchmark_family") or "layer1").strip().lower()
            if pfam != fam:
                continue
            run_id = str(payload.get("run_id") or path.stem)
            for row in payload.get("cases") or []:
                if not isinstance(row, dict):
                    continue
                if str(row.get("case_id")) != cid:
                    continue
                return {
                    "run_id": run_id,
                    "completed_at": payload.get("completed_at"),
                    "status": row.get("status"),
                }
        return None

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a full run detail (metrics/predicted/gold per case).

        Raises:
            RunPayloadTooLargeError: Run exceeds case-count or on-disk size limits.
        """
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                return None
            main_path = self._persisted_main_json_path(run_id)
            if self._full_run_blocked(rec, main_path):
                raise RunPayloadTooLargeError(FULL_RUN_BLOCK_DETAIL)
            return self._run_to_dict(rec)

    def get_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """Compact run payload for suite analytics (no per-case result blobs).

        Built without serializing full case ``result`` payloads. For runs with more than
        ``_SUMMARY_CASES_INLINE_MAX`` cases, ``cases`` is omitted; use
        :meth:`get_run_cases_page` with pagination.
        """
        with self._lock:
            rec = self._runs.get(run_id)
        if rec:
            summary = self._run_to_summary_dict(rec, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX)
            main_path = self._persisted_main_json_path(run_id)
            self._annotate_full_run_guard(summary, rec=rec, main_json_path=main_path)
            return summary
        hist = self._history_dir()
        leg = self._legacy_history_dir()
        main_path = hist / f"{run_id}.json"
        if not main_path.is_file():
            alt = leg / f"{run_id}.json"
            main_path = alt if alt.is_file() else main_path
        sidecar = hist / f"{run_id}.summary.json"
        if sidecar.is_file() and main_path.is_file():
            try:
                summary = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                summary = None
            if isinstance(summary, dict) and summary.get("run_id") == run_id:
                self._annotate_full_run_guard(summary, rec=None, main_json_path=main_path)
                return summary
        if main_path.is_file():
            try:
                payload = json.loads(main_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                return None
            summary = self._persisted_payload_to_summary_dict(
                payload, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX
            )
            if summary is not None:
                self._annotate_full_run_guard(summary, rec=None, main_json_path=main_path)
            return summary
        return None

    def get_run_cases_page(
        self,
        run_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any] | None:
        """Return a page of slim case rows (no ``result`` blobs) for large runs."""
        if offset < 0 or limit < 1:
            return None
        with self._lock:
            rec = self._runs.get(run_id)
        if rec:
            return self._run_cases_page_from_record(rec, offset=offset, limit=limit)
        path = self._history_dir() / f"{run_id}.json"
        if not path.is_file():
            leg = self._legacy_history_dir() / f"{run_id}.json"
            path = leg if leg.is_file() else path
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return None
        return self._persisted_payload_to_cases_page(payload, offset=offset, limit=limit)

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

    def _run_root_fixtures_layer2(self) -> Path:
        """Return path to layer-2 semantic benchmark fixtures root."""
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "tests" / "fixtures" / "benchmarks" / "layer2"

    def _history_dir(self) -> Path:
        """Directory for durable run JSON snapshots."""
        if self._history_dir_override is not None:
            d = self._history_dir_override
        else:
            repo_root = Path(__file__).resolve().parents[2]
            d = repo_root / "data" / "benchmark_runs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _legacy_history_dir(self) -> Path:
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "data" / "benchmark_run_history"

    def _load_persisted_runs(self) -> None:
        """Restore persisted runs on process startup."""
        paths = list(self._history_dir().glob("*.json"))
        legacy_dir = self._legacy_history_dir()
        if legacy_dir != self._history_dir() and legacy_dir.is_dir():
            paths.extend(legacy_dir.glob("*.json"))
        restored: dict[str, RunRecord] = {}
        for path in sorted(paths):
            if path.name.endswith(".summary.json"):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                rec = self._run_from_dict(payload)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            restored[rec.run_id] = rec
        if restored:
            self._runs.update(restored)

    def _persist_run_snapshot(self, rec: RunRecord) -> None:
        """Write run payload to disk (survives API restart)."""
        try:
            hist = self._history_dir()
            payload = self._run_to_dict(rec)
            path = hist / f"{rec.run_id}.json"
            path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            slim = self._run_to_summary_dict(rec, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX)
            self._annotate_full_run_guard(slim, rec=rec, main_json_path=path)
            (hist / f"{rec.run_id}.summary.json").write_text(
                json.dumps(slim, indent=2, default=str),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _delete_persisted_run(self, run_id: str) -> None:
        for path in (
            self._history_dir() / f"{run_id}.json",
            self._history_dir() / f"{run_id}.summary.json",
            self._legacy_history_dir() / f"{run_id}.json",
        ):
            try:
                if path.is_file():
                    path.unlink()
            except OSError:
                continue

    def _persisted_main_json_path(self, run_id: str) -> Path | None:
        """Return path to the full run JSON snapshot if it exists on disk."""
        hist = self._history_dir()
        primary = hist / f"{run_id}.json"
        if primary.is_file():
            return primary
        legacy = self._legacy_history_dir() / f"{run_id}.json"
        if legacy.is_file():
            return legacy
        return None

    def _full_run_blocked(self, rec: RunRecord, main_json_path: Path | None) -> bool:
        if len(rec.case_ids) > _FULL_RUN_MAX_CASE_IDS:
            return True
        if main_json_path is not None and main_json_path.is_file():
            try:
                if main_json_path.stat().st_size > _FULL_RUN_MAX_FILE_BYTES:
                    return True
            except OSError:
                return False
        return False

    def _annotate_full_run_guard(
        self,
        summary: dict[str, Any],
        *,
        rec: RunRecord | None,
        main_json_path: Path | None,
    ) -> None:
        """Set ``full_run_blocked`` / ``full_run_block_reason`` for UI (GET full run guard)."""
        reason: str | None = None
        if rec is not None:
            if self._full_run_blocked(rec, main_json_path):
                reason = FULL_RUN_BLOCK_DETAIL
        else:
            ct_raw = summary.get("cases_total")
            if ct_raw is None:
                ct_raw = len(summary.get("cases") or [])
            try:
                if int(ct_raw) > _FULL_RUN_MAX_CASE_IDS:
                    reason = FULL_RUN_BLOCK_DETAIL
            except (TypeError, ValueError):
                pass
            if reason is None and main_json_path is not None and main_json_path.is_file():
                try:
                    if main_json_path.stat().st_size > _FULL_RUN_MAX_FILE_BYTES:
                        reason = FULL_RUN_BLOCK_DETAIL
                except OSError:
                    pass
        summary["full_run_blocked"] = reason is not None
        summary["full_run_block_reason"] = reason

    def _run_from_dict(self, payload: dict[str, Any]) -> RunRecord:
        case_rows = payload.get("cases") or []
        case_ids = [str(row.get("case_id")) for row in case_rows if row.get("case_id")]
        rec = RunRecord(
            run_id=str(payload["run_id"]),
            label=payload.get("label"),
            case_ids=case_ids,
            benchmark_family=(payload.get("benchmark_family") or "layer1"),
            status=payload.get("status") or RunStatus.COMPLETED,
            created_at=payload.get("created_at") or _now_iso(),
            started_at=payload.get("started_at"),
            completed_at=payload.get("completed_at"),
            cancel_requested=bool(payload.get("cancel_requested")),
            error_message=payload.get("error_message"),
            run_config=dict(payload.get("run_config") or {}),
        )
        for row in case_rows:
            case_id = row.get("case_id")
            if not case_id or row.get("status") == "pending":
                continue
            rec.cases[str(case_id)] = RunCaseRecord(
                case_id=str(case_id),
                status=row.get("status") or "pending",
                result=row.get("result"),
                error_message=row.get("error_message"),
                finished_at=row.get("finished_at"),
            )
        if rec.status in (RunStatus.QUEUED, RunStatus.RUNNING):
            rec.status = RunStatus.FAILED
            rec.completed_at = rec.completed_at or _now_iso()
            rec.error_message = rec.error_message or "run_interrupted_after_api_restart"
        return rec

    def _run_one_case(self, run_id: str, case_id: str) -> dict[str, Any]:
        """Execute one benchmark case and return the run_case payload."""
        with self._lock:
            rec = self._runs.get(run_id)
            if not rec:
                raise KeyError(f"run_not_found:{run_id}")
            if rec.cancel_requested:
                raise RunCancelledError("cancel_requested")
            family = rec.benchmark_family
            run_config = dict(rec.run_config or {})

        settings = build_settings_for_run(run_config)

        if family == "layer2":
            fixture_dir = self._run_root_fixtures_layer2() / case_id
            if not fixture_dir.is_dir():
                raise FileNotFoundError(f"fixture_dir_not_found:{fixture_dir}")
            return self._layer2_runner(fixture_dir, settings=settings)

        fixture_dir = self._run_root_fixtures_layer1() / case_id
        if not fixture_dir.is_dir():
            raise FileNotFoundError(f"fixture_dir_not_found:{fixture_dir}")

        layer1_gold = run_config.get("layer1_gold") or {}
        external_gold_root = layer1_gold.get("external_gold_root")
        return self._layer1_runner(
            fixture_dir,
            settings=settings,
            external_gold_root=Path(external_gold_root) if external_gold_root else None,
            gold_filename=layer1_gold.get("gold_filename") or "gold.json",
            threshold_profile=run_config.get("threshold_profile"),
        )

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
            self._persist_run_snapshot(rec)

    def _case_result_summary(self, case_record: RunCaseRecord) -> dict[str, Any]:
        return _case_result_summary_static(case_record)

    def _run_to_dict(self, rec: RunRecord) -> dict[str, Any]:
        """Serialize a full run (progress + summaries + all case results)."""
        # Keep response stable for UI.
        counts = rec.progress_counts()
        # "cases" as array for deterministic ordering by case_ids.
        cases_out: list[dict[str, Any]] = []
        for cid in rec.case_ids:
            if cid in rec.cases:
                case_row = rec.cases[cid].to_dict()
                case_row["summary"] = self._case_result_summary(rec.cases[cid])
                cases_out.append(case_row)
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

        l2_recalls = []
        for r in ok_results:
            m = r.get("metrics") or {}
            if m.get("precision_methods") is not None:
                l2_recalls.append(_layer2_recall_ratio(m))

        return {
            "run_id": rec.run_id,
            "label": rec.label,
            "benchmark_family": rec.benchmark_family,
            "status": rec.status,
            "created_at": rec.created_at,
            "started_at": rec.started_at,
            "completed_at": rec.completed_at,
            "error_message": rec.error_message,
            "run_config": public_run_config(rec.run_config),
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
                "avg_layer2_recall_ratio": _mean(l2_recalls),
                "pass_count": len(
                    [
                        1
                        for c in rec.cases.values()
                        if c.status == "ok" and _case_contract_passed(c.result)
                    ]
                ),
                "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
                "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
                "case_count": counts["total"],
            },
            "cases": cases_out,
        }

    def _slim_case_row(self, cid: str, case_rec: RunCaseRecord | None) -> dict[str, Any]:
        if case_rec is None:
            return {"case_id": cid, "status": "pending"}
        return {
            "case_id": case_rec.case_id,
            "status": case_rec.status,
            "error_message": case_rec.error_message,
            "finished_at": case_rec.finished_at,
            "summary": _case_result_summary_static(case_rec),
        }

    def _run_aggregate_summary(self, rec: RunRecord) -> dict[str, Any]:
        counts = rec.progress_counts()
        ok_results = [c.result for c in rec.cases.values() if c.status == "ok" and c.result]
        f1_names = [_extract_case_f1_for_averages(r)["names_f1"] for r in ok_results]
        f1_arxiv = [_extract_case_f1_for_averages(r)["sample_arxiv_f1"] for r in ok_results]
        f1_doi = [_extract_case_f1_for_averages(r)["sample_doi_f1"] for r in ok_results]
        l2_recalls = []
        for r in ok_results:
            m = r.get("metrics") or {}
            if m.get("precision_methods") is not None:
                l2_recalls.append(_layer2_recall_ratio(m))
        return {
            "avg_names_f1": _mean(f1_names),
            "avg_sample_arxiv_f1": _mean(f1_arxiv),
            "avg_sample_doi_f1": _mean(f1_doi),
            "avg_layer2_recall_ratio": _mean(l2_recalls),
            "pass_count": len(
                [
                    1
                    for c in rec.cases.values()
                    if c.status == "ok" and _case_contract_passed(c.result)
                ]
            ),
            "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
            "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
            "case_count": counts["total"],
        }

    def _run_to_summary_dict(self, rec: RunRecord, *, inline_cases_limit: int) -> dict[str, Any]:
        """Like _run_to_dict but omits per-case ``result``; optionally omits ``cases`` when huge."""
        counts = rec.progress_counts()
        total = counts["total"]
        base: dict[str, Any] = {
            "run_id": rec.run_id,
            "label": rec.label,
            "benchmark_family": rec.benchmark_family,
            "status": rec.status,
            "created_at": rec.created_at,
            "started_at": rec.started_at,
            "completed_at": rec.completed_at,
            "error_message": rec.error_message,
            "run_config": public_run_config(rec.run_config),
            "progress": {
                "total": counts["total"],
                "completed": counts["completed"],
                "percent": (
                    (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
                ),
            },
            "summary": self._run_aggregate_summary(rec),
        }
        if total > inline_cases_limit:
            base["cases"] = []
            base["cases_paginated"] = True
            base["cases_total"] = total
        else:
            base["cases"] = [self._slim_case_row(cid, rec.cases.get(cid)) for cid in rec.case_ids]
            base["cases_paginated"] = False
            base["cases_total"] = total
        return base

    def _persisted_row_to_case_record(self, row: dict[str, Any]) -> RunCaseRecord:
        return RunCaseRecord(
            case_id=str(row.get("case_id") or ""),
            status=str(row.get("status") or "pending"),
            result=row.get("result") if isinstance(row.get("result"), dict) else None,
            error_message=row.get("error_message"),
            finished_at=row.get("finished_at"),
        )

    def _persisted_payload_to_summary_dict(
        self, payload: dict[str, Any], *, inline_cases_limit: int
    ) -> dict[str, Any] | None:
        """Build summary dict from on-disk JSON (reuses RunRecord shape, no ``get_run``)."""
        try:
            rec = self._run_from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return None
        return self._run_to_summary_dict(rec, inline_cases_limit=inline_cases_limit)

    def _run_cases_page_from_record(
        self, rec: RunRecord, *, offset: int, limit: int
    ) -> dict[str, Any]:
        total = len(rec.case_ids)
        slice_ids = rec.case_ids[offset : offset + limit]
        items = [self._slim_case_row(cid, rec.cases.get(cid)) for cid in slice_ids]
        return {
            "run_id": rec.run_id,
            "benchmark_family": rec.benchmark_family,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
        }

    def _persisted_payload_to_cases_page(
        self, payload: dict[str, Any], *, offset: int, limit: int
    ) -> dict[str, Any]:
        case_rows = [r for r in (payload.get("cases") or []) if isinstance(r, dict)]
        case_ids = [str(r.get("case_id")) for r in case_rows if r.get("case_id")]
        total = len(case_ids)
        slice_ids = case_ids[offset : offset + limit]
        row_by_id = {str(r.get("case_id")): r for r in case_rows if r.get("case_id")}
        items: list[dict[str, Any]] = []
        for cid in slice_ids:
            row = row_by_id.get(cid)
            if not row:
                items.append({"case_id": cid, "status": "pending"})
            else:
                cr = self._persisted_row_to_case_record(row)
                items.append(self._slim_case_row(cid, cr))
        return {
            "run_id": payload.get("run_id"),
            "benchmark_family": payload.get("benchmark_family"),
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
        }

    def _run_summary_to_dict(self, rec: RunRecord) -> dict[str, Any]:
        """Serialize a compact run row for the runs list."""
        # Summary for runs list.
        counts = rec.progress_counts()
        return {
            "run_id": rec.run_id,
            "label": rec.label,
            "benchmark_family": rec.benchmark_family,
            "status": rec.status,
            "created_at": rec.created_at,
            "started_at": rec.started_at,
            "completed_at": rec.completed_at,
            "run_config": public_run_config(rec.run_config),
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
                "avg_layer2_recall_ratio": _mean(
                    [
                        _layer2_recall_ratio(c.result.get("metrics") or {})
                        for c in rec.cases.values()
                        if c.status == "ok" and c.result
                    ]
                ),
                "pass_count": len(
                    [
                        1
                        for c in rec.cases.values()
                        if c.status == "ok" and c.result and _case_contract_passed(c.result)
                    ]
                ),
                "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
                "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
                "case_count": counts["total"],
            },
        }


# A process-level singleton used by the API router.
task_store = BenchmarkTaskStore(max_workers=2)
