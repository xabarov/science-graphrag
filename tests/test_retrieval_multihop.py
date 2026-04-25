from __future__ import annotations

from pathlib import Path

import httpx

from eval.retrieval.multihop_runner import (
    discover_multihop_cases,
    run_multihop_case,
    score_multihop_case,
)


def test_score_multihop_case_precision_recall() -> None:
    metrics = score_multihop_case(
        ["a", "b", "c"],
        ["a", "b", "x"],
        min_precision=0.7,
        min_recall=0.5,
    )
    assert metrics["passed"] is False
    assert metrics["precision"] == 0.666667
    assert metrics["recall"] == 0.666667
    assert metrics["missing_work_ids"] == ["c"]
    assert metrics["unexpected_work_ids"] == ["x"]


def test_discover_multihop_mini_cases() -> None:
    fixtures = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "benchmarks"
        / "retrieval"
        / "multihop_v1"
    )
    cases = discover_multihop_cases(fixtures, tier="multihop_mini")
    ids = {x.name for x in cases}
    assert len(ids) == 5
    assert "mh_01_yolov1_cites" in ids


def test_run_multihop_case_with_mocked_api(monkeypatch, tmp_path: Path) -> None:
    case_dir = tmp_path / "mh_demo"
    case_dir.mkdir()
    (case_dir / "question.json").write_text(
        """
{
  "center_work_id": "center-1",
  "depth": 2,
  "neighbor_limit": 300,
  "expected_neighbor_work_ids": ["w1", "w2", "w3"],
  "min_precision": 0.7,
  "min_recall": 0.5
}
        """.strip(),
        encoding="utf-8",
    )

    class _Resp:
        status_code = 200

        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def json() -> dict:
            return {
                "nodes": [
                    {"id": "center-1", "type": "Work"},
                    {"id": "w1", "type": "Work"},
                    {"id": "w2", "type": "Work"},
                    {"id": "noise-method", "type": "Method"},
                ]
            }

    def _fake_get(self, url: str, params: dict | None = None):  # noqa: ANN001
        assert "/v1/works/center-1/graph" in url
        assert params and params.get("depth") == 2
        return _Resp()

    monkeypatch.setattr(httpx.Client, "get", _fake_get)
    report = run_multihop_case(
        case_dir,
        api_base_url="http://localhost:8000",
        timeout_seconds=5.0,
    )
    assert report["metrics"]["passed"] is True
    assert report["metrics"]["precision"] == 1.0
    assert report["metrics"]["recall"] == 0.666667
