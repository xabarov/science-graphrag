from __future__ import annotations

from pathlib import Path

from science_graphrag.config import Settings
from science_graphrag.ingestion.stage_context import build_ingest_run_context


def test_ingest_run_context_creates_stores(monkeypatch, tmp_path: Path) -> None:
    created = {"neo": 0, "qdrant": 0, "blob": 0}

    class DummyNeo:
        def __init__(self, *_args, **_kwargs):
            created["neo"] += 1

        def close(self) -> None:
            return

    class DummyQdrant:
        def __init__(self, *_args, **_kwargs):
            created["qdrant"] += 1

    class DummyBlob:
        def __init__(self, *_args, **_kwargs):
            created["blob"] += 1

    monkeypatch.setattr("science_graphrag.ingestion.stage_context.Neo4jGraphStore", DummyNeo)
    monkeypatch.setattr("science_graphrag.ingestion.stage_context.QdrantChunkStore", DummyQdrant)
    monkeypatch.setattr("science_graphrag.ingestion.stage_context.BlobStore", DummyBlob)

    settings = Settings(
        blob_root=tmp_path / "blobs",
        artifact_root=tmp_path / "artifacts",
    )
    ctx = build_ingest_run_context(settings=settings, source_path=tmp_path / "doc.md")

    _ = ctx.neo4j_store
    _ = ctx.neo4j_store
    _ = ctx.qdrant_store
    _ = ctx.qdrant_store
    _ = ctx.blob_store
    _ = ctx.blob_store

    assert created == {"neo": 1, "qdrant": 1, "blob": 1}
    ctx.close()
