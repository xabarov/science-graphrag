"""Corpus file discovery for batch ingest CLI."""

from __future__ import annotations

from pathlib import Path

CORPUS_SUPPORTED_SUFFIXES = frozenset({".pdf", ".md", ".txt"})


def discover_corpus_files(directory: Path) -> list[Path]:
    """Sorted list of ingestible files under directory (recursive)."""

    found: list[Path] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in CORPUS_SUPPORTED_SUFFIXES:
            found.append(path)
    return found


__all__ = ["CORPUS_SUPPORTED_SUFFIXES", "discover_corpus_files"]
