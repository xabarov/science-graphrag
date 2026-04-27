"""Protocols for artifact I/O seams (local disk + optional S3 via ``S3ArtifactStore``)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Protocol members are stubs; see ``LocalFilesystemArtifactStore`` / ``S3ArtifactStore``.
# pylint: disable=missing-function-docstring,unnecessary-ellipsis


class ArtifactStorePort(Protocol):
    """
    Deterministic artifacts keyed by paths relative to a single root (``artifact_root``).

    ``glob_under_entries`` returns ``(relative_path, mtime)`` for each match (``Path.glob``
    semantics), used when sorting legacy ingest paths.
    """

    @property
    def root(self) -> Path: ...

    def absolute(self, relative: Path) -> Path: ...

    def write_text(
        self,
        relative: Path,
        text: str,
        *,
        encoding: str = "utf-8",
    ) -> Path: ...

    def read_text(
        self,
        relative: Path,
        *,
        encoding: str = "utf-8",
        errors: str | None = None,
    ) -> str: ...

    def exists(self, relative: Path) -> bool: ...

    def stat_st_size(self, relative: Path) -> int: ...

    def glob_under(self, pattern: str) -> list[Path]: ...

    def glob_under_entries(self, pattern: str) -> list[tuple[Path, float]]: ...
