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
from pathlib import Path
from threading import Lock
from typing import Any

from eval.layer1.runner import run_case as run_layer1_case
from eval.layer2.runner import run_case as run_layer2_case
from science_graphrag.api import task_benchmark_serializers as bench_ser
from science_graphrag.api.benchmark_profiles import (
    build_settings_for_run,
    prepare_run_config,
)
from science_graphrag.api.task_benchmark_models import (
    FULL_RUN_BLOCK_DETAIL,
    FULL_RUN_MAX_CASE_IDS,
    FULL_RUN_MAX_FILE_BYTES,
    SUMMARY_CASES_INLINE_MAX,
    RunCancelledError,
    RunCaseRecord,
    RunPayloadTooLargeError,
    RunRecord,
    RunStatus,
    now_iso,
)
from science_graphrag.artifacts.run_layout import (
    default_benchmark_run_history_legacy_dir,
    default_benchmark_runs_dir,
)

# Mutable module-level limits (tests monkeypatch these attributes).
_SUMMARY_CASES_INLINE_MAX = SUMMARY_CASES_INLINE_MAX
_FULL_RUN_MAX_CASE_IDS = FULL_RUN_MAX_CASE_IDS
_FULL_RUN_MAX_FILE_BYTES = FULL_RUN_MAX_FILE_BYTES


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
            rec.started_at = now_iso()
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
            if rec.status == RunStatus.QUEUED:
                rec.status = RunStatus.CANCELLED
                rec.completed_at = now_iso()
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
        """Scan recent persisted run JSON files for the latest completed row for ``case_id``."""
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
            paths.sort(key=str, reverse=True)
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
            if bench_ser.full_run_blocked(
                rec,
                main_path,
                max_case_ids=_FULL_RUN_MAX_CASE_IDS,
                max_file_bytes=_FULL_RUN_MAX_FILE_BYTES,
            ):
                raise RunPayloadTooLargeError(FULL_RUN_BLOCK_DETAIL)
            return bench_ser.run_to_full_api_dict(rec)

    def get_run_summary(self, run_id: str) -> dict[str, Any] | None:
        """Compact run payload for suite analytics (no per-case result blobs)."""
        with self._lock:
            rec = self._runs.get(run_id)
        if rec:
            summary = bench_ser.run_to_summary_dict(
                rec, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX
            )
            main_path = self._persisted_main_json_path(run_id)
            bench_ser.annotate_full_run_guard(
                summary,
                rec=rec,
                main_json_path=main_path,
                max_case_ids=_FULL_RUN_MAX_CASE_IDS,
                max_file_bytes=_FULL_RUN_MAX_FILE_BYTES,
            )
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
                bench_ser.annotate_full_run_guard(
                    summary,
                    rec=None,
                    main_json_path=main_path,
                    max_case_ids=_FULL_RUN_MAX_CASE_IDS,
                    max_file_bytes=_FULL_RUN_MAX_FILE_BYTES,
                )
                return summary
        if main_path.is_file():
            try:
                payload = json.loads(main_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, TypeError):
                return None
            summary = bench_ser.persisted_payload_to_summary_dict(
                payload, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX
            )
            if summary is not None:
                bench_ser.annotate_full_run_guard(
                    summary,
                    rec=None,
                    main_json_path=main_path,
                    max_case_ids=_FULL_RUN_MAX_CASE_IDS,
                    max_file_bytes=_FULL_RUN_MAX_FILE_BYTES,
                )
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
            return bench_ser.run_cases_page_from_record(rec, offset=offset, limit=limit)
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
        return bench_ser.persisted_payload_to_cases_page(payload, offset=offset, limit=limit)

    def list_runs_summary(self) -> list[dict[str, Any]]:
        """List run summaries for the runs table."""
        with self._lock:
            records = list(self._runs.values())
            return [bench_ser.run_summary_list_row(r) for r in records]

    def _run_root_fixtures_layer1(self) -> Path:
        """Return path to layer-1 benchmark fixtures root."""
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
            d.mkdir(parents=True, exist_ok=True)
            return d
        return default_benchmark_runs_dir()

    def _legacy_history_dir(self) -> Path:
        return default_benchmark_run_history_legacy_dir()

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
                rec = bench_ser.run_from_dict(payload)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
            restored[rec.run_id] = rec
        if restored:
            self._runs.update(restored)

    def _persist_run_snapshot(self, rec: RunRecord) -> None:
        """Write run payload to disk (survives API restart)."""
        try:
            hist = self._history_dir()
            payload = bench_ser.run_to_full_api_dict(rec)
            path = hist / f"{rec.run_id}.json"
            path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            slim = bench_ser.run_to_summary_dict(rec, inline_cases_limit=_SUMMARY_CASES_INLINE_MAX)
            bench_ser.annotate_full_run_guard(
                slim,
                rec=rec,
                main_json_path=path,
                max_case_ids=_FULL_RUN_MAX_CASE_IDS,
                max_file_bytes=_FULL_RUN_MAX_FILE_BYTES,
            )
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

        finished_at = now_iso()

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
                rec.completed_at = now_iso()
                if rec.cancel_requested and all(
                    cr.status == "cancelled" for cr in rec.cases.values()
                ):
                    rec.status = RunStatus.CANCELLED
                elif any(cr.status == "failed" for cr in rec.cases.values()):
                    rec.status = RunStatus.FAILED
                else:
                    rec.status = RunStatus.COMPLETED
            self._persist_run_snapshot(rec)


task_store = BenchmarkTaskStore(max_workers=2)
