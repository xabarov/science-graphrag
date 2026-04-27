"""Artifact taxonomy, benchmark path registry, and local filesystem seam (Phase 0)."""

from __future__ import annotations

from science_graphrag.artifacts import benchmark_paths, benchmark_registry, run_layout
from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.artifacts.taxonomy import (
    ArtifactClass,
    ArtifactDescriptor,
    ArtifactFamily,
    StoragePolicy,
)

__all__ = [
    "ArtifactClass",
    "ArtifactDescriptor",
    "ArtifactFamily",
    "StoragePolicy",
    "LocalFilesystemArtifactStore",
    "benchmark_paths",
    "benchmark_registry",
    "run_layout",
]
