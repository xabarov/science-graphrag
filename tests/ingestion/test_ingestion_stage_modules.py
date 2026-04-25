from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from science_graphrag.config import Settings
from science_graphrag.ingestion.stages.chunking import run_chunking
from science_graphrag.ingestion.stages.claims import run_claims
from science_graphrag.ingestion.stages.embeddings import run_embeddings
from science_graphrag.ingestion.stages.neo4j_upsert import run_neo4j_upsert
from science_graphrag.ingestion.stages.qdrant_upsert import run_qdrant_upsert
from science_graphrag.ingestion.stages.semantic import run_semantic
from science_graphrag.ingestion.stages.vl_pdf import run_vl_pdf
from science_graphrag.ingestion.stages.workspace_attach import run_workspace_attach


class _DummyCtx:
    def __init__(self) -> None:
        self.settings = Settings(extraction_llm_enabled=False, claims_extraction_enabled=True)
        self.ingest_workspace_ids = ["ws-1"]
        self.neo4j_store = SimpleNamespace(
            upsert_work_layer1=lambda *args, **kwargs: None,
            workspace_add_work=lambda *args, **kwargs: True,
        )

    @contextmanager
    def stage(self, _stage):
        class _Handle:
            def metric(self, _k, _v):
                return

        yield _Handle()


def test_run_vl_pdf() -> None:
    ctx = _DummyCtx()
    text, mode = run_vl_pdf(
        ctx,
        source_path=SimpleNamespace(),
        markdown_loader=lambda _path: ("markdown", "vl"),
    )
    assert text == "markdown"
    assert mode == "vl"


def test_run_chunking(monkeypatch) -> None:
    ctx = _DummyCtx()
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.chunking.chunk_document_for_retrieval",
        lambda *_args, **_kwargs: [SimpleNamespace(text="a")],
    )
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.chunking.dedupe_chunks_for_embedding",
        lambda chunks: chunks,
    )
    chunks = run_chunking(ctx, normalized_text="hello")
    assert len(chunks) == 1


def test_run_claims(monkeypatch) -> None:
    ctx = _DummyCtx()
    chunks = [SimpleNamespace(text="x", chunk_fingerprint="cfp", section_path=["s"])]
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.claims.extract_claims_llm",
        lambda *_args, **_kwargs: [SimpleNamespace(claim_text="c1")],
    )
    out = run_claims(ctx, work_id="w1", chunks=chunks)
    assert len(out) == 1


def test_run_semantic(monkeypatch) -> None:
    ctx = _DummyCtx()
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.semantic.extract_semantic_method_dataset",
        lambda *_args, **_kwargs: {"ok": True},
    )
    assert run_semantic(ctx, document_id="d1", normalized_text="t") == {"ok": True}


def test_run_neo4j_upsert() -> None:
    called = {"ok": False}
    ctx = _DummyCtx()

    def _upsert(*_args, **_kwargs):
        called["ok"] = True

    ctx.neo4j_store = SimpleNamespace(upsert_work_layer1=_upsert)
    run_neo4j_upsert(
        ctx,
        work_id="w1",
        draft=SimpleNamespace(),
        authorships=[],
        venue_id=None,
        institution_nodes=[],
    )
    assert called["ok"] is True


def test_run_embeddings(monkeypatch) -> None:
    ctx = _DummyCtx()

    class _Embedder:
        dim = 4

        def embed(self, _texts):
            return [[0.1, 0.2, 0.3, 0.4]]

    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.embeddings.resolve_embedder",
        lambda _settings: _Embedder(),
    )
    embedder, vectors = run_embeddings(ctx, texts=["hello"])
    assert embedder.dim == 4
    assert len(vectors) == 1


def test_run_qdrant_upsert(monkeypatch) -> None:
    ctx = _DummyCtx()
    calls = {"chunk": 0, "work": 0, "claims": 0}

    class _QChunk:
        def __init__(self, *_args, **_kwargs):
            return

        def delete_points_by_document_id(self, **_kwargs):
            calls["chunk"] += 1

        def upsert_document_chunks(self, **_kwargs):
            calls["chunk"] += 1

    class _QWork:
        def __init__(self, *_args, **_kwargs):
            return

        def upsert_work_summary(self, **_kwargs):
            calls["work"] += 1

    class _QClaims:
        def __init__(self, *_args, **_kwargs):
            return

        def delete_points_by_work_id(self, **_kwargs):
            calls["claims"] += 1

        def upsert_claims(self, **_kwargs):
            calls["claims"] += 1

    monkeypatch.setattr("science_graphrag.ingestion.stages.qdrant_upsert.QdrantChunkStore", _QChunk)
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.qdrant_upsert.QdrantWorkEmbeddingStore",
        _QWork,
    )
    monkeypatch.setattr(
        "science_graphrag.ingestion.stages.qdrant_upsert.QdrantClaimsStore",
        _QClaims,
    )
    run_qdrant_upsert(
        ctx,
        work_id="w1",
        document_id="d1",
        chunks=[],
        chunk_vectors=[],
        work_vector=[0.1],
        embedder=SimpleNamespace(dim=1),
        claim_rows=[SimpleNamespace(claim_text="c1")],
    )
    assert calls["chunk"] == 2
    assert calls["work"] == 1
    assert calls["claims"] == 2


def test_run_workspace_attach() -> None:
    called = {"ok": False}
    ctx = _DummyCtx()
    ctx.neo4j_store = SimpleNamespace(
        workspace_add_work=lambda *_args: called.__setitem__("ok", True)
    )
    run_workspace_attach(ctx, work_id="w1")
    assert called["ok"] is True
