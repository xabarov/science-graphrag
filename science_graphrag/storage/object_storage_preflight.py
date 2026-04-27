"""Optional connectivity check for S3/MinIO (operator pre-flight)."""

from __future__ import annotations

from science_graphrag.config import Settings
from science_graphrag.storage.s3_client import build_s3_client, ensure_bucket_exists


def probe_object_storage(settings: Settings) -> None:
    """Head bucket + list (MaxKeys=1). Raises on misconfiguration or network errors."""

    if not settings.object_storage_enabled:
        return
    client = build_s3_client(settings)
    ensure_bucket_exists(settings, client=client)
    name = (settings.s3_bucket or "").strip()
    client.list_objects_v2(Bucket=name, MaxKeys=1)
