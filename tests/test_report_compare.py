"""Tests for benchmark report comparator."""

from __future__ import annotations

from eval.report_compare import compare_reports


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
