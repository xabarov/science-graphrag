"""Unit tests for Neo4j semantic relations benchmark (patched, no live stack)."""

from __future__ import annotations

from pathlib import Path

from eval.relations_v1 import runner as relations_runner
from science_graphrag.config import Settings
from science_graphrag.domain.semantic_models import (
    SemanticDatasetV1,
    SemanticExtractionV1,
    SemanticMethodV1,
)

FIXTURE_ATSS = (
    Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer2" / "atss_semantic"
)


def test_relations_run_case_smoke(monkeypatch) -> None:
    """Patch ingest and Neo4j reads so CI does not need live services."""

    def _settings() -> Settings:
        return Settings(
            extraction_llm_api_key=None,
            extraction_llm_enabled=True,
            semantic_graph_confidence_threshold=0.35,
        )

    def _fake_ingest_document(path: Path, *, settings: Settings, session=None):
        del session
        assert path.name == "atss_semantic.md"
        assert settings.reuse_cached_markdown is False
        return "doc-atss", "work-atss"

    def _fake_query_semantic_projection(
        settings: Settings,
        work_id: str,
        document_id: str,
    ) -> SemanticExtractionV1:
        del settings
        assert work_id == "work-atss"
        assert document_id == "doc-atss"
        return SemanticExtractionV1(
            document_id=document_id,
            methods=[
                SemanticMethodV1(name="Adaptive Training Sample Selection (ATSS)", confidence=1.0),
                SemanticMethodV1(name="FCOS", confidence=1.0),
            ],
            datasets=[SemanticDatasetV1(name="MS COCO", confidence=1.0)],
            relations=[],
        )

    class _FakeNeo:
        def __init__(self, *args, **_kwargs):
            self.args = args

        def wipe_all(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("eval.relations_v1.runner.get_settings", _settings)
    monkeypatch.setattr("eval.relations_v1.runner.ingest_document", _fake_ingest_document)
    monkeypatch.setattr(
        "eval.relations_v1.runner._query_semantic_projection",
        _fake_query_semantic_projection,
    )
    monkeypatch.setattr("eval.relations_v1.runner.Neo4jGraphStore", _FakeNeo)

    report = relations_runner.run_case(FIXTURE_ATSS)
    assert report["case_id"] == "atss_semantic"
    assert report["work_id"] == "work-atss"
    m = report["metrics"]
    assert "precision_methods" in m
    assert "recall_methods_num" in m
    assert "predicted_from_neo4j" in report
