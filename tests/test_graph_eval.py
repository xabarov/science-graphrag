"""Graph-level eval unit/smoke tests."""

from __future__ import annotations

from pathlib import Path

from eval.graph_v1.metrics import GraphSnapshot, score_graph_snapshot
from eval.graph_v1.runner import run_case
from eval.layer1.spec import Layer1GoldSpec
from science_graphrag.config import Settings

FIXTURE_YOLO = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1" / "yolov1"


def test_graph_expectations_load() -> None:
    """Graph expectations should load from shared gold.json."""

    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    assert spec.graph_expectations is not None
    assert spec.graph_expectations.min_cites == 23
    assert "1505.00110" in spec.graph_expectations.expected_cited_arxiv_ids


def test_score_graph_snapshot() -> None:
    """Snapshot scoring should honor graph expectation ranges."""

    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    expected_arxiv_ids = spec.graph_expectations.expected_cited_arxiv_ids  # type: ignore[union-attr]
    snapshot = GraphSnapshot(
        work_id="work-1",
        work_title="You Only Look Once: Unified, Real-Time Object Detection",
        authorship_count=4,
        institution_count=2,
        cites_count=23,
        cited_arxiv_ids=expected_arxiv_ids,
        duplicate_work_fingerprints=0,
    )
    metrics = score_graph_snapshot(snapshot, spec)
    assert metrics["cites_range_ok"] is True
    assert metrics["authorships_range_ok"] is True
    assert metrics["institutions_range_ok"] is True
    assert metrics["cited_arxiv_f1"] == 1.0
    assert metrics["duplicate_work_fingerprints_ok"] is True


def test_graph_run_case_smoke(monkeypatch) -> None:
    """Patch ingest and graph reads so CI does not need live services."""

    def _settings() -> Settings:
        return Settings(
            extraction_llm_api_key=None,
            extraction_llm_enabled=False,
        )

    def _fake_ingest_document(path: Path, *, settings: Settings, session=None):
        del session
        assert path.name == "yolov1.md"
        assert settings.reuse_cached_markdown is False
        return "doc-1", "work-1"

    def _fake_query_graph_snapshot(settings: Settings, work_id: str) -> GraphSnapshot:
        del settings
        assert work_id == "work-1"
        return GraphSnapshot(
            work_id="work-1",
            work_title="You Only Look Once: Unified, Real-Time Object Detection",
            authorship_count=4,
            institution_count=2,
            cites_count=23,
            cited_arxiv_ids=["1505.00110", "1310.1531"],
            duplicate_work_fingerprints=0,
        )

    class _FakeNeo:
        def __init__(self, *args, **_kwargs):
            self.args = args

        def wipe_all(self) -> None:
            """Pretend to clear graph state."""

            return None

        def close(self) -> None:
            """Pretend to close graph connection."""

            return None

    monkeypatch.setattr("eval.graph_v1.runner.get_settings", _settings)
    monkeypatch.setattr("eval.graph_v1.runner.ingest_document", _fake_ingest_document)
    monkeypatch.setattr("eval.graph_v1.runner._query_graph_snapshot", _fake_query_graph_snapshot)
    monkeypatch.setattr("eval.graph_v1.runner.Neo4jGraphStore", _FakeNeo)

    report = run_case(FIXTURE_YOLO)
    assert report["case_id"] == "yolov1"
    assert report["document_id"] == "doc-1"
    assert report["work_id"] == "work-1"
    assert report["metrics"]["snapshot"]["cites_count"] == 23
