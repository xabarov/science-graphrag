"""Ingest markdown cache path policy and lookup helpers.

Resolution order for ``read_cached_markdown``:

1. Canonical document-scoped artifacts
   (``ingestion/<document_id>/article.md`` then ``normalized.md``).
2. Legacy slug mirror under ``articles/<slug>/article.md``.
3. Migration-only glob ``ingestion/*/<slug>/article.md`` (newest mtime first).

New writes should prefer document-scoped paths only; slug mirrors remain for backward compatibility.
"""

from __future__ import annotations

import re
from pathlib import Path

from science_graphrag.artifacts.protocols import ArtifactStorePort
from science_graphrag.config import Settings
from science_graphrag.ingestion.artifact_layout import (
    canonical_article_md_rel,
    canonical_normalized_md_rel,
    strip_ingest_artifact_header,
)
from science_graphrag.storage.s3_artifact_store import build_artifact_store
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.cache_policy")


def slug(value: str) -> str:
    """Normalize arbitrary text to a cache-safe slug."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized or "document"


def article_slug(path: Path) -> str:
    """Return slug derived from source file stem."""
    return slug(path.stem)


def canonical_article_rel(source_path: Path) -> Path:
    """Return canonical article markdown path for a source file."""
    return Path("articles") / article_slug(source_path) / "article.md"


def canonical_diagnostics_rel(source_path: Path) -> Path:
    """Return canonical diagnostics path for a source file."""
    return Path("articles") / article_slug(source_path) / "extraction_diagnostics.json"


def legacy_slug_ingestion_article_paths(store: ArtifactStorePort, source_path: Path) -> list[Path]:
    """Legacy per-slug paths under arbitrary document folders (pre-document-id cache layout)."""
    pattern = f"ingestion/*/{article_slug(source_path)}/article.md"
    legacy_sorted = sorted(
        store.glob_under_entries(pattern),
        key=lambda item: item[1],
        reverse=True,
    )
    return [rel for rel, _ in legacy_sorted]


def read_cached_markdown(
    settings: Settings,
    source_path: Path,
    *,
    document_id: str | None = None,
    artifact_store: ArtifactStorePort | None = None,
    bypass_cache: bool = False,
) -> tuple[str, str] | None:
    """Read cached markdown using ordered candidate paths."""
    if bypass_cache:
        return None

    store = artifact_store or build_artifact_store(settings)
    candidate_rels: list[Path] = []
    if document_id:
        candidate_rels.append(canonical_article_md_rel(document_id))
        candidate_rels.append(canonical_normalized_md_rel(document_id))
    candidate_rels.append(canonical_article_rel(source_path))
    candidate_rels.extend(legacy_slug_ingestion_article_paths(store, source_path))
    seen: set[str] = set()
    for rel in candidate_rels:
        key = rel.as_posix()
        if key in seen:
            continue
        seen.add(key)
        if not store.exists(rel):
            continue
        text = store.read_text(rel, encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        mode = "cached-markdown"
        mode_match = re.search(r"extraction_mode=([a-zA-Z0-9\\-]+)", first_line)
        if mode_match:
            mode = mode_match.group(1)
        elif rel.name == "normalized.md":
            mode = "cached-normalized"
        logger.warning(
            "Reusing cached article markdown path=%s rel=%s source=%s document_id=%s mode=%s",
            store.absolute(rel),
            rel.as_posix(),
            source_path.name,
            document_id or "—",
            mode,
        )
        return strip_ingest_artifact_header(text), mode
    return None
