from pathlib import Path

from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.config import Settings
from science_graphrag.ingestion._pipeline_impl import _write_markdown_artifact
from science_graphrag.ingestion.cache_policy import canonical_article_rel, read_cached_markdown


def test_write_markdown_artifact_also_updates_canonical_article(tmp_path: Path):
    settings = Settings.model_construct(artifact_root=tmp_path)
    source = Path("/tmp/YOLOv1.pdf")
    store = LocalFilesystemArtifactStore(tmp_path)

    run_path = _write_markdown_artifact(
        settings=settings,
        document_id="doc-1",
        source_path=source,
        markdown="# Title\n\nBody",
        extraction_mode="vl",
        artifact_store=store,
    )

    canonical = tmp_path / canonical_article_rel(source)
    assert run_path.exists()
    assert canonical.exists()
    assert "extraction_mode=vl" in canonical.read_text(encoding="utf-8")


def test_read_cached_markdown_prefers_canonical_article(tmp_path: Path):
    settings = Settings.model_construct(artifact_root=tmp_path, reuse_cached_markdown=True)
    source = Path("/tmp/YOLOv1.pdf")
    canonical = tmp_path / canonical_article_rel(source)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        "<!-- source=YOLOv1.pdf extraction_mode=vl -->\n\n# Cached Title\n\nCached body",
        encoding="utf-8",
    )
    store = LocalFilesystemArtifactStore(tmp_path)

    cached = read_cached_markdown(settings, source, artifact_store=store)

    assert cached == ("# Cached Title\n\nCached body", "vl")
