"""Content-addressed raw blob storage: local disk or S3/MinIO."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Protocol

from botocore.exceptions import ClientError

from science_graphrag.config import Settings
from science_graphrag.storage.blobs import BlobStore
from science_graphrag.storage.object_keys import raw_blob_object_key


class RawBlobStorePort(Protocol):
    """SHA256-addressed PDF/source bytes (same contract as ``BlobStore`` for ingest + API)."""

    def store_file(self, source_path: Path) -> tuple[str, Path]:
        """Copy or upload file; returns (sha256_hex, local_path_for_pipeline_reads)."""

    def path_for_sha(self, sha256_hex: str) -> Path:
        """Return a local path to bytes if available (may download from S3 into cache)."""


class LocalRawBlobStore:
    """Delegates to existing ``BlobStore``."""

    def __init__(self, blob_root: Path) -> None:
        self._inner = BlobStore(blob_root)

    def store_file(self, source_path: Path) -> tuple[str, Path]:
        """Persist under ``blob_root/raw``; see ``BlobStore.store_file``."""
        return self._inner.store_file(source_path)

    def path_for_sha(self, sha256_hex: str) -> Path:
        """Resolved path on local blob tree (may not exist)."""
        return self._inner.path_for_sha(sha256_hex)

    def close(self) -> None:
        """No-op (compat with ``StoreRegistry.close``)."""
        return


class S3RawBlobStore:
    """Raw blobs in S3; local legacy path + disk cache under ``blob_root``."""

    def __init__(self, client: Any, bucket: str, blob_root: Path) -> None:
        self._client = client
        self._bucket = bucket
        self._blob_root = Path(blob_root)
        self._legacy = BlobStore(self._blob_root)
        self._cache_root = self._blob_root / "_s3_raw_cache"

    def store_file(self, source_path: Path) -> tuple[str, Path]:
        """Upload bytes to S3; return sha and original ``source_path`` for pipeline reads."""
        data = source_path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        key = raw_blob_object_key(sha)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return sha, source_path

    def path_for_sha(self, sha256_hex: str) -> Path:
        """Prefer on-disk legacy blob; else download from S3 into ``_s3_raw_cache``."""
        sha = sha256_hex.strip().lower()
        legacy = self._legacy.path_for_sha(sha)
        if legacy.is_file():
            return legacy
        key = raw_blob_object_key(sha)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError:
            return legacy
        cache_path = self._cache_root / sha[:2] / sha
        if cache_path.is_file():
            return cache_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        body = resp["Body"].read()
        tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp.write_bytes(body)
        tmp.replace(cache_path)
        return cache_path

    def close(self) -> None:
        """No-op."""
        return


def build_raw_blob_store(settings: Settings) -> RawBlobStorePort:
    """Return S3-backed raw blob store (legacy on-disk blobs remain readable as migration path)."""
    from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
        build_s3_client,
        ensure_bucket_exists,
    )

    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    return S3RawBlobStore(client, settings.s3_bucket, settings.blob_root)
