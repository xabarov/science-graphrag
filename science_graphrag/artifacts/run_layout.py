"""Repo-relative layout for UI benchmark run snapshots.

Compact ``*.summary.json`` files stay under ``data/benchmark_runs``; full ``*.json`` payloads
are stored in S3 (mandatory object storage).
"""

from __future__ import annotations

from pathlib import Path

from science_graphrag.artifacts import benchmark_paths as bp
from science_graphrag.artifacts.taxonomy import (
    ArtifactClass,
    ArtifactDescriptor,
    ArtifactFamily,
    StoragePolicy,
)

RUN_HISTORY_PRIMARY_REL = Path("data/benchmark_runs")
RUN_HISTORY_LEGACY_REL = Path("data/benchmark_run_history")

RUN_HISTORY_DESCRIPTOR = ArtifactDescriptor(
    logical_id="run_history.ui_benchmark_snapshots",
    artifact_class=ArtifactClass.RUNTIME,
    family=ArtifactFamily.RUN_HISTORY,
    policy=StoragePolicy.OBJECT_STORE,
    default_repo_relative=str(RUN_HISTORY_PRIMARY_REL).replace("\\", "/"),
    committable=False,
)


def default_benchmark_runs_dir(repo_root: Path | None = None) -> Path:
    """Primary directory for persisted UI benchmark runs (creates if missing)."""
    root = repo_root if repo_root is not None else bp.REPO_ROOT
    d = root / RUN_HISTORY_PRIMARY_REL
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_benchmark_run_history_legacy_dir(repo_root: Path | None = None) -> Path:
    """Legacy run history directory (read/migrate only)."""
    root = repo_root if repo_root is not None else bp.REPO_ROOT
    return root / RUN_HISTORY_LEGACY_REL
