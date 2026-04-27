"""Ingest artifact taxonomy (logical ids; paths remain in ``ingestion.artifact_layout``).

Document-scoped markdown lives under ``artifact_root`` with deterministic relative segments
defined by ``canonical_*_md_rel`` helpers. Phase 0 keeps path construction in one module and
uses ``LocalFilesystemArtifactStore`` for I/O at call sites.
"""

from __future__ import annotations

from science_graphrag.artifacts.taxonomy import ArtifactClass, ArtifactFamily, StoragePolicy

# Stable logical ids for documentation and future DB manifest rows (no filename coupling).
INGEST_DOCUMENT_NORMALIZED_MD = "ingest.document.normalized_md"
INGEST_DOCUMENT_ARTICLE_MD = "ingest.document.article_md"
INGEST_DOCUMENT_ARTICLE_LEGACY = "ingest.document.article_legacy_slug"

INGEST_BODY_CLASS = ArtifactClass.CANONICAL
INGEST_BODY_FAMILY = ArtifactFamily.INGEST
# Heavy ingest markdown is a prime MinIO candidate in later phases; today it is local disk.
INGEST_BODY_POLICY = StoragePolicy.OBJECT_BACKED_LATER
