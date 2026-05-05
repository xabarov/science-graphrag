"""Regression tests for progress store and cache policy seams."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.ingestion.cache_policy import read_cached_markdown
from science_graphrag.ingestion.progress_store import append_progress, load_progress


class _DummyStore:
    def __init__(self, mapping: dict[str, str]) -> None:
        """Store text payloads by relative artifact path."""
        self._mapping = mapping

    def glob_under_entries(self, _pattern: str):
        """No legacy entries in this unit-test dummy."""
        return []

    def exists(self, rel: Path) -> bool:
        """Return True when a relative path exists in mapping."""
        return rel.as_posix() in self._mapping

    def read_text(self, rel: Path, encoding: str = "utf-8") -> str:  # noqa: ARG002
        """Return stored text payload for relative path."""
        del encoding
        return self._mapping[rel.as_posix()]

    def absolute(self, rel: Path) -> str:
        """Return synthetic absolute path for logging assertions."""
        return f"/tmp/{rel.as_posix()}"


def test_progress_store_load_and_append(tmp_path: Path) -> None:
    """Progress file should keep latest status per path."""
    progress_file = tmp_path / "progress.jsonl"
    append_progress(progress_file, {"path": "/a.md", "status": "ok"})
    append_progress(progress_file, {"path": "/b.md", "status": "fail"})
    loaded = load_progress(progress_file)
    assert loaded == {"/a.md": "ok", "/b.md": "fail"}


def test_read_cached_markdown_uses_document_id_path_first(tmp_path: Path) -> None:
    """Document-id canonical path should be preferred when present."""
    source = tmp_path / "paper.pdf"
    source.write_text("x", encoding="utf-8")
    store = _DummyStore(
        {"ingestion/doc-1/article.md": ("<!-- extraction_mode=vl -->\n" "# Header\n" "Body")}
    )
    cached = read_cached_markdown(
        settings=object(),  # type: ignore[arg-type]
        source_path=source,
        document_id="doc-1",
        artifact_store=store,  # type: ignore[arg-type]
    )
    assert cached is not None
    text, mode = cached
    assert mode == "vl"
    assert "Header" in text
