"""Logical object key layout for S3/MinIO (Phase 1 raw + ingest queue)."""

from __future__ import annotations

from pathlib import Path


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
