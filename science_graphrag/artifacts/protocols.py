"""Protocols for artifact I/O seams (Phase 0: local implementation, later object store)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Protocol members are stubs; see ``LocalFilesystemArtifactStore`` for concrete behavior.
# pylint: disable=missing-function-docstring


class ArtifactStorePort(Protocol):
    """Deterministic artifacts keyed by paths relative to a single root (``artifact_root``)."""

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
