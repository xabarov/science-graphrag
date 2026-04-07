"""Tests for benchmark report comparator."""

from __future__ import annotations

from eval.report_compare import (
    compare_reports,
    compare_result_to_markdown,
    normalize_api_run_for_compare,
)


def test_compare_reports_detects_regression_and_improvement() -> None:
    baseline = {
        "run_metadata": {"model": "a", "prompt": "x"},
        "cases": [
            {
                "case_id": "alpha",
                "metrics": {
                    "contract": {"passed": True},
                    "references": {"sample_arxiv_f1": 1.0},
                },
            }
        ],
    }
    current = {
        "run_metadata": {"model": "b", "prompt": "x"},
        "cases": [
            {
                "case_id": "alpha",
                "metrics": {
                    "contract": {"passed": False},
                    "references": {"sample_arxiv_f1": 0.5},
                },
            }
        ],
    }
    out = compare_reports(baseline, current)
    assert out["summary"]["regression_count"] >= 2
    assert out["run_metadata_delta"]["model"]["baseline"] == "a"
    assert out["run_metadata_delta"]["model"]["current"] == "b"


def test_normalize_api_run_for_compare_extracts_metrics() -> None:
    api_run = {
        "run_id": "r1",
        "label": "a",
        "benchmark_family": "layer1",
        "run_config": {"model_profile": "p1"},
        "cases": [
            {
                "case_id": "c1",
                "status": "ok",
                "result": {
                    "metrics": {"contract": {"passed": True}, "authorships": {"names_f1": 0.9}}
                },
            },
            {"case_id": "c2", "status": "failed", "result": None},
        ],
    }
    norm, skipped = normalize_api_run_for_compare(api_run)
    assert len(norm["cases"]) == 1
    assert norm["cases"][0]["case_id"] == "c1"
    assert norm["cases"][0]["metrics"]["authorships"]["names_f1"] == 0.9
    assert norm["run_metadata"]["cfg_model_profile"] == "p1"
    assert any(s["case_id"] == "c2" for s in skipped)


def test_compare_result_to_markdown_contains_labels() -> None:
    baseline = {
        "run_metadata": {},
        "cases": [
            {
                "case_id": "solo",
                "metrics": {"references": {"sample_arxiv_f1": 1.0}},
            }
        ],
    }
    current = {
        "run_metadata": {},
        "cases": [
            {
                "case_id": "solo",
                "metrics": {"references": {"sample_arxiv_f1": 0.9}},
            }
        ],
    }
    out = compare_reports(baseline, current)
    md = compare_result_to_markdown(out, baseline_label="run-a", current_label="run-b")
    assert "run-a" in md
    assert "run-b" in md
    assert "Regressions" in md


def test_compare_reports_handles_single_case_wrapped_format() -> None:
    baseline = {
        "run_metadata": {},
        "case": {"case_id": "solo", "metrics": {"contract": {"passed": False}}},
    }
    current = {
        "run_metadata": {},
        "case": {"case_id": "solo", "metrics": {"contract": {"passed": True}}},
    }
    out = compare_reports(baseline, current)
    assert out["summary"]["improvement_count"] >= 1
