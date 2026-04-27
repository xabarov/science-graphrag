"""Artifact taxonomy for Phase 0 (registry + storage seam).

Logical classes align with docs/analysis/minio-integration-and-artifact-storage-roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ArtifactClass(str, Enum):
    """Lifecycle / review posture of an artifact."""

    CANONICAL = "canonical"
    RUNTIME = "runtime"
    DIAGNOSTIC = "diagnostic"
    REPORT = "report"


class ArtifactFamily(str, Enum):
    """Domain grouping (independent of on-disk layout)."""

    INGEST = "ingest"
    BENCHMARK = "benchmark"
    CHAT_AGENT = "chat_agent"
    OD_DIAGNOSTICS = "od_diagnostics"
    RUN_HISTORY = "run_history"


class StoragePolicy(str, Enum):
    """Where the artifact is intended to live long-term."""

    GIT_TRACKED = "git_tracked"
    LOCAL_RUNTIME = "local_runtime"
    OBJECT_BACKED_LATER = "object_backed_later"
    DB_AUTHORITATIVE = "db_authoritative"


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Static registry entry: logical id + taxonomy + default repo-relative location."""

    logical_id: str
    artifact_class: ArtifactClass
    family: ArtifactFamily
    policy: StoragePolicy
    default_repo_relative: str
    committable: bool
    """True if the artifact is intended for git / review bundles (sanitized)."""
