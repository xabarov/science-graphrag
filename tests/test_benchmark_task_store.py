"""Focused tests for benchmark task storage and restore behavior."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from science_graphrag.api.task_store import (
    FULL_RUN_BLOCK_DETAIL,
    BenchmarkTaskStore,
    RunPayloadTooLargeError,
)


def _wait_for_terminal(
    store: BenchmarkTaskStore, run_id: str, *, timeout_s: float = 5.0
) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        run = store.get_run(run_id)
        if run and run.get("status") in {"completed", "failed", "cancelled"}:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run did not reach terminal status: {run_id}")


def test_task_store_persists_and_restores_runs(tmp_path: Path) -> None:
    history_dir = tmp_path / "benchmark_runs"

    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {"work_metadata": {"title": settings.extraction_llm_model}},
            "gold": {"work_metadata": {"title": gold_filename}},
            "diagnostics": {},
        }

    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=history_dir,
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["yolov1"],
        label="persist-me",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default", "gold_source": "curated_gold"},
    )

    run = _wait_for_terminal(store, run_id)
    assert run["status"] == "completed"
    assert (history_dir / f"{run_id}.json").is_file()

    restored_store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=history_dir,
        layer1_runner=_fake_layer1_runner,
    )
    restored = restored_store.get_run(run_id)
    assert restored is not None
    assert restored["status"] == "completed"
    assert restored["label"] == "persist-me"


def test_task_store_applies_model_and_gold_run_config(tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        captured["fixture_dir"] = fixture_dir
        captured["model"] = settings.extraction_llm_model
        captured["external_gold_root"] = external_gold_root
        captured["gold_filename"] = gold_filename
        captured["threshold_profile"] = threshold_profile
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 0.9},
                "references": {"sample_arxiv_f1": 0.8, "sample_doi_f1": 0.7},
            },
            "predicted": {"work_metadata": {"title": settings.extraction_llm_model}},
            "gold": {"work_metadata": {"title": gold_filename}},
            "diagnostics": {},
        }

    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=tmp_path / "benchmark_runs",
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["atss_realpdf"],
        label="student-vs-teacher",
        benchmark_family="layer1",
        run_config={
            "model_profile": "student_mistral_small_32",
            "gold_source": "teacher_gold",
            "threshold_profile": "student_mistral",
        },
    )

    run = _wait_for_terminal(store, run_id)
    assert run["run_config"]["model_profile"] == "student_mistral_small_32"
    assert run["run_config"]["resolved_model_id"] == "mistralai/mistral-small-3.2-24b-instruct"
    assert captured["model"] == "mistralai/mistral-small-3.2-24b-instruct"
    assert captured["gold_filename"] == "gold_teacher.json"
    assert captured["threshold_profile"] == "student_mistral"
    assert captured["external_gold_root"] is not None
    assert str(captured["external_gold_root"]).endswith("eval/teacher_gold/layer1")


def test_task_store_get_run_summary_omits_case_results(tmp_path: Path) -> None:
    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {"blob": "large"},
            "gold": {},
            "diagnostics": {},
        }

    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=tmp_path / "benchmark_runs",
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["yolov1"],
        label="sum-test",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default"},
    )
    run = _wait_for_terminal(store, run_id)
    assert run["cases"][0].get("result") is not None
    slim = store.get_run_summary(run_id)
    assert slim is not None
    assert "result" not in slim["cases"][0]
    assert slim["cases"][0]["case_id"] == "yolov1"


def test_get_run_summary_paginated_when_over_inline_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "science_graphrag.api.benchmark_task_store_core._SUMMARY_CASES_INLINE_MAX", 1
    )

    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {"blob": "large"},
            "gold": {},
            "diagnostics": {},
        }

    store = BenchmarkTaskStore(
        max_workers=2,
        history_dir=tmp_path / "benchmark_runs",
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["yolov1", "atss_realpdf"],
        label="paginated-summary",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default"},
    )
    run = _wait_for_terminal(store, run_id)
    assert len(run["cases"]) == 2
    slim = store.get_run_summary(run_id)
    assert slim is not None
    assert slim.get("cases_paginated") is True
    assert slim.get("cases") == []
    assert slim.get("cases_total") == 2
    page = store.get_run_cases_page(run_id, offset=0, limit=10)
    assert page is not None
    assert page["total"] == 2
    assert len(page["items"]) == 2
    assert {row["case_id"] for row in page["items"]} == {"yolov1", "atss_realpdf"}


def test_find_last_run_hint_prefers_newer_file(tmp_path: Path) -> None:
    hist = tmp_path / "benchmark_runs"
    hist.mkdir(parents=True)
    rid_old = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    rid_new = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    old_payload: dict[str, Any] = {
        "run_id": rid_old,
        "status": "completed",
        "completed_at": "2020-01-01T00:00:00+00:00",
        "benchmark_family": "layer1",
        "cases": [{"case_id": "yolov1", "status": "ok"}],
    }
    new_payload: dict[str, Any] = {
        "run_id": rid_new,
        "status": "completed",
        "completed_at": "2025-01-01T00:00:00+00:00",
        "benchmark_family": "layer1",
        "cases": [{"case_id": "yolov1", "status": "failed"}],
    }
    p_old = hist / f"{rid_old}.json"
    p_new = hist / f"{rid_new}.json"
    p_old.write_text(json.dumps(old_payload), encoding="utf-8")
    p_new.write_text(json.dumps(new_payload), encoding="utf-8")
    os.utime(p_old, (time.time() - 200, time.time() - 200))
    os.utime(p_new, (time.time(), time.time()))

    def _noop_layer1_runner(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise AssertionError("should not run cases in this test")

    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_noop_layer1_runner,
    )
    hint = store.find_last_run_hint_for_case("yolov1", "layer1", max_files=50)
    assert hint is not None
    assert hint["run_id"] == rid_new
    assert hint["status"] == "failed"
    assert hint["completed_at"] == "2025-01-01T00:00:00+00:00"


def test_persist_writes_summary_sidecar(tmp_path: Path) -> None:
    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {},
            "gold": {},
            "diagnostics": {},
        }

    hist = tmp_path / "benchmark_runs"
    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["yolov1"],
        label="sidecar-test",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default"},
    )
    _wait_for_terminal(store, run_id)
    sidecar = hist / f"{run_id}.summary.json"
    assert sidecar.is_file()
    slim = json.loads(sidecar.read_text(encoding="utf-8"))
    assert slim.get("run_id") == run_id
    assert slim.get("full_run_blocked") is False


def test_get_run_raises_when_case_count_over_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {},
            "gold": {},
            "diagnostics": {},
        }

    store = BenchmarkTaskStore(
        max_workers=2,
        history_dir=tmp_path / "benchmark_runs",
        layer1_runner=_fake_layer1_runner,
    )
    run_id = store.create_run(
        case_ids=["yolov1", "atss_realpdf"],
        label="over-limit",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default"},
    )
    _wait_for_terminal(store, run_id)
    monkeypatch.setattr("science_graphrag.api.benchmark_task_store_core._FULL_RUN_MAX_CASE_IDS", 1)
    slim = store.get_run_summary(run_id)
    assert slim is not None
    assert slim.get("full_run_blocked") is True
    assert slim.get("full_run_block_reason") == FULL_RUN_BLOCK_DETAIL
    with pytest.raises(RunPayloadTooLargeError):
        store.get_run(run_id)


def test_task_store_remote_full_payload_roundtrip_in_memory(tmp_path: Path) -> None:
    """Remote persistence path without real S3 (ThreadPoolExecutor breaks moto patching)."""

    class _MemoryRemotePersistence:
        """Minimal S3-shaped persistence for Phase 3 task_store tests."""

        remote_full_payloads = True

        def __init__(self) -> None:
            self._objects: dict[str, str] = {}

        def put_full_json(self, run_id: str, json_text: str) -> str | None:
            key = f"science-benchmarks/runs/{run_id}/full.json"
            self._objects[key] = json_text
            return key

        def get_full_json(self, run_id: str, *, object_key: str | None = None) -> str | None:
            key = (object_key or "").strip() or f"science-benchmarks/runs/{run_id}/full.json"
            return self._objects.get(key)

        def delete_full_json(self, run_id: str, *, object_key: str | None = None) -> None:
            key = (object_key or "").strip() or f"science-benchmarks/runs/{run_id}/full.json"
            self._objects.pop(key, None)

        def close(self) -> None:
            return None

    def _fake_layer1_runner(
        fixture_dir: Path,
        *,
        settings,
        external_gold_root=None,
        gold_filename: str = "gold.json",
        threshold_profile: str | None = None,
    ) -> dict[str, Any]:
        del external_gold_root, gold_filename, threshold_profile
        return {
            "case_id": fixture_dir.name,
            "metrics": {
                "contract": {"passed": True, "checks": {}},
                "authorships": {"names_f1": 1.0},
                "references": {"sample_arxiv_f1": 1.0, "sample_doi_f1": 1.0},
            },
            "predicted": {},
            "gold": {},
            "diagnostics": {},
        }

    persistence = _MemoryRemotePersistence()
    hist = tmp_path / "benchmark_runs"
    hist.mkdir(parents=True, exist_ok=True)
    store = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_fake_layer1_runner,
        persistence=persistence,
    )
    run_id = store.create_run(
        case_ids=["yolov1"],
        label="remote-persist",
        benchmark_family="layer1",
        run_config={"model_profile": "env_default", "gold_source": "curated_gold"},
    )
    _wait_for_terminal(store, run_id)
    # Ensure the last _persist_run_snapshot finished before we read disk for restore
    # (ThreadPoolExecutor callback vs. non-atomic summary write).
    store._executor.shutdown(wait=True)  # pylint: disable=protected-access
    assert not (hist / f"{run_id}.json").is_file()
    summary = json.loads((hist / f"{run_id}.summary.json").read_text(encoding="utf-8"))
    assert summary.get("full_run_object_key")
    assert summary.get("full_run_json_bytes")

    restored = BenchmarkTaskStore(
        max_workers=1,
        history_dir=hist,
        layer1_runner=_fake_layer1_runner,
        persistence=persistence,
    )
    full = restored.get_run(run_id)
    assert full is not None
    assert full["status"] == "completed"
    assert full["label"] == "remote-persist"
