"""Logical object key layout for S3/MinIO (Phase 1 raw + ingest queue; Phase 2 artifacts)."""

from __future__ import annotations

from pathlib import Path

# Ingest markdown / diagnostics under the same bucket as Phase 1, separate prefix (roadmap §7.2).
DEFAULT_S3_ARTIFACT_KEY_PREFIX = "science-artifacts"


def raw_blob_object_key(sha256_hex: str) -> str:
    """S3 key for content-addressed raw bytes (two-char prefix shard)."""
    sha = sha256_hex.strip().lower()
    if len(sha) < 2:
        return f"blobs/raw/__/{sha}"
    return f"blobs/raw/{sha[:2]}/{sha}"


def ingest_queue_object_key(job_id: str, filename: str) -> str:
    """S3 key for a single queued ingest upload."""
    suffix = Path(filename or "upload").suffix.lower()
    return f"ingest-queue/{job_id}{suffix}"


def normalize_artifact_relative(relative: Path) -> str:
    """Return POSIX path under artifact root; reject absolute paths and ``..`` segments."""
    p = Path(relative)
    if p.is_absolute():
        msg = f"artifact relative path must be relative: {relative!r}"
        raise ValueError(msg)
    parts = p.parts
    if ".." in parts:
        msg = f"artifact relative path must not contain '..': {relative!r}"
        raise ValueError(msg)
    return p.as_posix()


def ingest_artifact_object_key(
    relative: Path, *, prefix: str = DEFAULT_S3_ARTIFACT_KEY_PREFIX
) -> str:
    """
    Full S3 object key for an ingest artifact.

    Maps the same logical layout as local ``artifact_root`` (e.g. ``ingestion/<id>/article.md``,
    legacy ``articles/<slug>/article.md``) under ``prefix/``.
    """
    rel = normalize_artifact_relative(relative)
    base = prefix.strip().strip("/")
    if not base:
        return rel
    return f"{base}/{rel}"


def relative_artifact_from_object_key(
    key: str,
    *,
    prefix: str = DEFAULT_S3_ARTIFACT_KEY_PREFIX,
) -> Path | None:
    """If ``key`` is under ``prefix/``, return the path relative to artifact root; else None."""
    base = prefix.strip().strip("/")
    if not base:
        return Path(key)
    pre = f"{base}/"
    if not key.startswith(pre):
        return None
    return Path(key[len(pre) :])
