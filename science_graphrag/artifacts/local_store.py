"""Local filesystem implementation of the ingest artifact store seam (Phase 0)."""

from __future__ import annotations

from pathlib import Path


class LocalFilesystemArtifactStore:
    """Deterministic text/binary artifacts under a single root (``artifact_root``)."""

    def __init__(self, root: Path) -> None:
        """Create store rooted at ``root`` (typically ``Settings.artifact_root``)."""
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def absolute(self, relative: Path) -> Path:
        """Absolute path for a key relative to ``artifact_root``."""
        return self.root / relative

    def write_text(
        self,
        relative: Path,
        text: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        """Write UTF-8 text at a deterministic relative path; return absolute path."""
        path = self.absolute(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return path

    def read_text(
        self,
        relative: Path,
        *,
        encoding: str = "utf-8",
        errors: str | None = None,
    ) -> str:
        """Read UTF-8 text from a relative path."""
        path = self.absolute(relative)
        return path.read_text(encoding=encoding, errors=errors or "strict")

    def exists(self, relative: Path) -> bool:
        """True if ``relative`` points to an existing regular file."""
        return self.absolute(relative).is_file()

    def stat_st_size(self, relative: Path) -> int:
        """Return ``st_size`` for a relative file path."""
        return int(self.absolute(relative).stat().st_size)

    def glob_under_entries(self, pattern: str) -> list[tuple[Path, float]]:
        """Return ``(relative_to_root, mtime)`` for each matching file."""
        out: list[tuple[Path, float]] = []
        for path in self.root.glob(pattern):
            if path.is_file():
                rel = path.relative_to(self.root)
                out.append((rel, path.stat().st_mtime))
        return out

    def glob_under(self, pattern: str) -> list[Path]:
        """Glob under ``root``; returns absolute paths (sort in caller if needed)."""
        return [self.absolute(rel) for rel, _ in self.glob_under_entries(pattern)]
