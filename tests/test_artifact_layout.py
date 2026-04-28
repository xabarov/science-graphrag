"""Tests for canonical ingest artifact path resolution (ADR 022)."""

from __future__ import annotations

from pathlib import Path

from science_graphrag.api.works.detail import read_work_extracted_body_dict
from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.config import Settings
from science_graphrag.ingestion.artifact_layout import (
    canonical_article_md_rel,
    canonical_normalized_md_rel,
    resolve_extracted_body_file,
    strip_ingest_artifact_header,
)


def test_strip_ingest_artifact_header_removes_comment() -> None:
    raw = "<!-- source=paper.pdf extraction_mode=vl -->\n\n# Title\n\nbody"
    assert strip_ingest_artifact_header(raw).startswith("# Title")


def test_resolve_extracted_body_prefers_normalized(tmp_path: Path) -> None:
    doc_id = "doc-111"
    base = tmp_path / "ingestion" / doc_id
    base.mkdir(parents=True)
    (base / "normalized.md").write_text("norm-only", encoding="utf-8")
    (base / "article.md").write_text(
        "<!-- source=x.pdf extraction_mode=vl -->\n\narticle-body",
        encoding="utf-8",
    )
    store = LocalFilesystemArtifactStore(tmp_path)
    settings = Settings()
    hit = resolve_extracted_body_file(settings, doc_id, artifact_store=store)
    assert hit is not None
    path, label = hit
    assert label == "normalized"
    assert path.read_text(encoding="utf-8") == "norm-only"


def test_resolve_extracted_body_legacy_slug(tmp_path: Path) -> None:
    doc_id = "doc-222"
    legacy = tmp_path / "ingestion" / doc_id / "my-paper" / "article.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        "<!-- source=x extraction_mode=pypdf-fallback -->\n\nlegacy", encoding="utf-8"
    )
    store = LocalFilesystemArtifactStore(tmp_path)
    settings = Settings()
    hit = resolve_extracted_body_file(settings, doc_id, artifact_store=store)
    assert hit is not None
    _path, label = hit
    assert label == "article_legacy"


def test_read_work_extracted_body_dict_from_settings(tmp_path: Path) -> None:
    doc_id = "doc-333"
    rel = canonical_normalized_md_rel(doc_id)
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("# Hello\n\nworld", encoding="utf-8")
    store = LocalFilesystemArtifactStore(tmp_path)
    settings = Settings()
    out = read_work_extracted_body_dict(
        settings,
        work_id="w-333",
        document_id=doc_id,
        max_chars=10_000,
        artifact_store=store,
    )
    assert out["available"] is True
    assert out["source"] == "normalized"
    assert "Hello" in out["text"]
    assert out["truncated"] is False


def test_read_work_extracted_body_strips_whole_document_fence(tmp_path: Path) -> None:
    """Old normalized.md may still contain a VL whole-document wrapper; API strips at read time."""
    doc_id = "doc-fence"
    rel = canonical_normalized_md_rel(doc_id)
    path = tmp_path / rel
    path.parent.mkdir(parents=True)
    path.write_text("```markdown\n# Title\n\nBody\n```", encoding="utf-8")
    store = LocalFilesystemArtifactStore(tmp_path)
    settings = Settings()
    out = read_work_extracted_body_dict(
        settings,
        work_id="w-fence",
        document_id=doc_id,
        max_chars=10_000,
        artifact_store=store,
    )
    assert out["available"] is True
    assert out["text"] == "# Title\n\nBody"


def test_canonical_rel_paths() -> None:
    assert canonical_article_md_rel("d") == Path("ingestion/d/article.md")
    assert canonical_normalized_md_rel("d") == Path("ingestion/d/normalized.md")
