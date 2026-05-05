from __future__ import annotations

from pathlib import Path


def test_document_orchestrator_does_not_import_pipeline_impl() -> None:
    target = Path("science_graphrag/ingestion/document_orchestrator.py")
    text = target.read_text(encoding="utf-8")
    assert "ingestion._pipeline_impl" not in text
