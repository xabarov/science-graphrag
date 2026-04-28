"""Ingest queue payload storage: local disk or S3/MinIO."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from botocore.exceptions import ClientError

from science_graphrag.config import Settings
from science_graphrag.storage.object_keys import ingest_queue_object_key


class IngestQueueStorePort(Protocol):
    """Queued upload bytes addressed by stable object keys."""

    def put(self, job_id: str, filename: str, data: bytes) -> str:
        """Persist payload; returns logical object key."""

    def get_to_path(self, object_key: str, dest: Path) -> None:
        """Materialize object bytes at dest (parent dirs created)."""

    def delete(self, object_key: str) -> None:
        """Best-effort removal after successful ingest."""


class LocalIngestQueueStore:
    """Legacy layout: ``blob_root/_ingest_queue/{job_id}{suffix}``."""

    def __init__(self, blob_root: Path) -> None:
        self._root = Path(blob_root)

    def put(self, job_id: str, filename: str, data: bytes) -> str:
        """Write queue file under ``_ingest_queue``; return logical object key."""
        key = ingest_queue_object_key(job_id, filename)
        path = self._local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def _local_path(self, object_key: str) -> Path:
        # object_key is ingest-queue/{job_id}{suffix}
        name = Path(object_key).name
        return self._root / "_ingest_queue" / name

    def get_to_path(self, object_key: str, dest: Path) -> None:
        """Copy queue file bytes to ``dest``."""
        src = self._local_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())

    def delete(self, object_key: str) -> None:
        """Remove local queue file if present."""
        path = self._local_path(object_key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


class S3IngestQueueStore:
    """S3-backed queue payloads under ``ingest-queue/`` prefix."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def put(self, job_id: str, filename: str, data: bytes) -> str:
        """Upload queue payload to S3; return object key."""
        key = ingest_queue_object_key(job_id, filename)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        return key

    def get_to_path(self, object_key: str, dest: Path) -> None:
        """Download S3 object to ``dest``."""
        resp = self._client.get_object(Bucket=self._bucket, Key=object_key)
        body = resp["Body"].read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)

    def delete(self, object_key: str) -> None:
        """Delete S3 object; ignore client errors."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=object_key)
        except ClientError:
            pass


def build_ingest_queue_store(settings: Settings) -> IngestQueueStorePort:
    """Return S3-backed ingest queue store (MinIO or AWS S3-compatible API)."""
    from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
        build_s3_client,
        ensure_bucket_exists,
    )

    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    return S3IngestQueueStore(client, settings.s3_bucket)
