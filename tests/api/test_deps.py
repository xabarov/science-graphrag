from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from science_graphrag.api import deps


def test_get_stores_raises_without_init() -> None:
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    with pytest.raises(RuntimeError, match="StoreRegistry not initialized"):
        deps.get_stores(request)  # type: ignore[arg-type]


def test_store_registry_fields() -> None:
    registry = deps.StoreRegistry(
        neo4j=object(),  # type: ignore[arg-type]
        qdrant_chunks=object(),  # type: ignore[arg-type]
        qdrant_works=object(),  # type: ignore[arg-type]
        qdrant_claims=object(),  # type: ignore[arg-type]
        blob=object(),  # type: ignore[arg-type]
    )
    assert registry.neo4j is not None
    assert registry.qdrant_chunks is not None
    assert registry.qdrant_works is not None
    assert registry.qdrant_claims is not None
    assert registry.blob is not None


def test_init_close_cycle(monkeypatch: Any) -> None:
    calls: dict[str, int] = {"neo4j_close": 0}

    class _FakeNeo4j:
        def close(self) -> None:
            calls["neo4j_close"] += 1

    class _FakeQdrant:
        pass

    class _FakeBlob:
        pass

    monkeypatch.setattr(deps, "Neo4jGraphStore", lambda *_a, **_k: _FakeNeo4j())
    monkeypatch.setattr(deps, "QdrantChunkStore", lambda *_a, **_k: _FakeQdrant())
    monkeypatch.setattr(deps, "QdrantWorkEmbeddingStore", lambda *_a, **_k: _FakeQdrant())
    monkeypatch.setattr(deps, "QdrantClaimsStore", lambda *_a, **_k: _FakeQdrant())
    monkeypatch.setattr(deps, "BlobStore", lambda *_a, **_k: _FakeBlob())
    monkeypatch.setattr(deps, "resolve_embedding_dim", lambda **_k: 64)

    settings = SimpleNamespace(
        neo4j_uri="bolt://x",
        neo4j_user="u",
        neo4j_password="p",
        qdrant_url="http://q",
        qdrant_collection="chunks",
        qdrant_work_embeddings_collection="works",
        qdrant_claims_collection="claims",
        embedding_model=None,
        openrouter_embedding_model=None,
        openrouter_embedding_dim=1024,
        blob_root="data/blobs",
    )

    deps.close_store_registry()
    registry = deps.init_store_registry(settings)  # type: ignore[arg-type]
    assert registry.neo4j is not None
    deps.close_store_registry()
    assert calls["neo4j_close"] == 1
