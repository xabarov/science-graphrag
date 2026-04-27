"""Phase 0: local filesystem artifact store seam."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.ingestion.artifact_layout import (
    canonical_normalized_md_rel,
    resolve_extracted_body_relative,
)


def test_write_read_roundtrip(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    rel = Path("ingestion") / "d1" / "normalized.md"
    store.write_text(rel, "hello")
    assert store.exists(rel)
    assert store.read_text(rel) == "hello"
    assert store.stat_st_size(rel) == len("hello")


def test_resolve_extracted_body_uses_store(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    doc_id = "doc-x"
    store.write_text(canonical_normalized_md_rel(doc_id), "norm body")
    hit = resolve_extracted_body_relative(store, doc_id)
    assert hit is not None
    rel, label = hit
    assert label == "normalized"
    assert rel == canonical_normalized_md_rel(doc_id)


def test_glob_under_entries_legacy_article(tmp_path: Path) -> None:
    store = LocalFilesystemArtifactStore(tmp_path)
    doc_id = "doc-y"
    legacy = Path("ingestion") / doc_id / "slug-a" / "article.md"
    store.write_text(legacy, "x")
    entries = store.glob_under_entries(f"ingestion/{doc_id}/*/article.md")
    assert len(entries) == 1
    assert entries[0][0] == legacy
