"""Application-level store registry — shared by API, agent runtime, and retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from science_graphrag.artifacts.protocols import ArtifactStorePort
from science_graphrag.artifacts.run_layout import default_benchmark_runs_dir
from science_graphrag.config import Settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.benchmark_run_persistence import (
    BenchmarkRunPersistencePort,
    build_benchmark_run_persistence,
)
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_claims_store import QdrantClaimsStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore
from science_graphrag.storage.raw_blob_store import RawBlobStorePort, build_raw_blob_store
from science_graphrag.storage.s3_artifact_store import build_artifact_store


@dataclass
class StoreRegistry:
    """Application-level registry for shared infrastructure stores."""

    neo4j: Neo4jGraphStore
    qdrant_chunks: QdrantChunkStore
    qdrant_works: QdrantWorkEmbeddingStore
    qdrant_claims: QdrantClaimsStore
    blob: RawBlobStorePort
    artifacts: ArtifactStorePort
    benchmark_runs: BenchmarkRunPersistencePort

    def close(self) -> None:
        for store in (
            self.neo4j,
            self.qdrant_chunks,
            self.qdrant_works,
            self.qdrant_claims,
            self.blob,
            self.artifacts,
            self.benchmark_runs,
        ):
            closer = getattr(store, "close", None)
            if callable(closer):
                closer()


_registry: StoreRegistry | None = None


def init_store_registry(settings: Settings) -> StoreRegistry:
    """Create and cache singleton store registry for app lifespan."""

    global _registry
    if _registry is not None:
        return _registry
    dim = resolve_embedding_dim(settings=settings)
    bench_hist = default_benchmark_runs_dir()
    _registry = StoreRegistry(
        neo4j=Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password),
        qdrant_chunks=QdrantChunkStore(
            settings.qdrant_url,
            settings.qdrant_collection,
            vector_dim=dim,
        ),
        qdrant_works=QdrantWorkEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_work_embeddings_collection,
            vector_dim=dim,
        ),
        qdrant_claims=QdrantClaimsStore(
            settings.qdrant_url,
            settings.qdrant_claims_collection,
            vector_dim=dim,
        ),
        blob=build_raw_blob_store(settings),
        artifacts=build_artifact_store(settings),
        benchmark_runs=build_benchmark_run_persistence(settings, bench_hist),
    )
    return _registry


def close_store_registry() -> None:
    """Close global store registry and reset cache."""

    global _registry
    if _registry is None:
        return
    _registry.close()
    _registry = None


def build_store_registry_for_tests(**overrides: Any) -> StoreRegistry:
    """Helper constructor for tests with optional field overrides."""

    required = {
        "neo4j",
        "qdrant_chunks",
        "qdrant_works",
        "qdrant_claims",
        "blob",
        "artifacts",
        "benchmark_runs",
    }
    missing = required.difference(overrides)
    if missing:
        raise ValueError(f"Missing required overrides: {sorted(missing)}")
    return StoreRegistry(**overrides)
