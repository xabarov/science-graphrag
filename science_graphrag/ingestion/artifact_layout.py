"""Canonical ingest artifact paths under ``artifact_root`` (document-scoped).

See docs/adr/022-reader-extracted-body-vs-qdrant-chunks.md.
"""

from __future__ import annotations

from pathlib import Path

from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore


def canonical_article_md_rel(document_id: str) -> Path:
    """Raw extraction markdown (may include HTML comment header)."""
    return Path("ingestion") / document_id / "article.md"


def canonical_normalized_md_rel(document_id: str) -> Path:
    """Normalized markdown/text used for LLM stages and chunking."""
    return Path("ingestion") / document_id / "normalized.md"


def strip_ingest_artifact_header(text: str) -> str:
    """Remove leading ``<!-- source=... extraction_mode=... -->`` block if present."""
    lines = text.splitlines()
    if lines and lines[0].startswith("<!-- ") and "extraction_mode=" in lines[0]:
        lines = lines[2:] if len(lines) > 1 and lines[1] == "" else lines[1:]
    return "\n".join(lines)


def resolve_extracted_body_relative(
    store: LocalFilesystemArtifactStore,
    document_id: str,
) -> tuple[Path, str] | None:
    """
    Return ``(path_relative_to_artifact_root, source_label)`` for the best body file, or None.

    Preference: ``normalized.md`` > ``article.md`` (canonical) > legacy slug path.
    ``source_label`` is ``normalized`` | ``article`` | ``article_legacy``.
    """

    norm = canonical_normalized_md_rel(document_id)
    if store.exists(norm):
        return norm, "normalized"
    art = canonical_article_md_rel(document_id)
    if store.exists(art):
        return art, "article"
    legacy_hits = sorted(
        store.glob_under(f"ingestion/{document_id}/*/article.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if legacy_hits:
        rel = legacy_hits[0].relative_to(store.root)
        return rel, "article_legacy"
    return None


def resolve_extracted_body_file(artifact_root: Path, document_id: str) -> tuple[Path, str] | None:
    """
    Return ``(absolute_path, source_label)`` for the best body file, or None.

    Preference: ``normalized.md`` > ``article.md`` (canonical) > legacy slug path.
    ``source_label`` is ``normalized`` | ``article`` | ``article_legacy``.
    """
    store = LocalFilesystemArtifactStore(Path(artifact_root))
    hit = resolve_extracted_body_relative(store, document_id)
    if hit is None:
        return None
    rel, label = hit
    return store.absolute(rel), label


def has_extracted_body_store(store: LocalFilesystemArtifactStore, document_id: str) -> bool:
    return resolve_extracted_body_relative(store, document_id) is not None


def has_extracted_body_file(artifact_root: Path, document_id: str) -> bool:
    return resolve_extracted_body_file(artifact_root, document_id) is not None
