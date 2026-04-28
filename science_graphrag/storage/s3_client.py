"""Shared boto3 S3 client factory for MinIO and AWS."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from botocore.config import Config
from botocore.exceptions import ClientError

from science_graphrag.config import Settings


@lru_cache(maxsize=16)
def _cached_client(
    endpoint_url: str | None,
    access_key: str,
    secret_key: str,
    use_ssl: bool,
    addressing_style: str,
) -> Any:
    # Import inside: optional heavy import for processes that never touch S3.
    import boto3  # pylint: disable=import-outside-toplevel

    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": addressing_style},
    )
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url or None,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        use_ssl=use_ssl,
        config=cfg,
    )


def build_s3_client(settings: Settings) -> Any:
    """Return a boto3 S3 client configured from settings (cached)."""

    ep = (settings.s3_endpoint_url or "").strip() or None
    ak = (settings.s3_access_key_id or "").strip()
    sk = (settings.s3_secret_access_key or "").strip()
    style = (settings.s3_addressing_style or "path").strip().lower()
    if style not in {"path", "virtual"}:
        style = "path"
    return _cached_client(ep, ak, sk, bool(settings.s3_use_ssl), style)


def ensure_bucket_exists(settings: Settings, client: Any | None = None) -> None:
    """Create bucket if missing (idempotent; safe for local MinIO)."""

    if client is None:
        client = build_s3_client(settings)
    name = (settings.s3_bucket or "").strip()
    if not name:
        return
    try:
        client.head_bucket(Bucket=name)
        return
    except ClientError as exc:
        code = (exc.response.get("Error") or {}).get("Code", "")
        if code not in {"404", "NoSuchBucket", "403"}:
            raise
    try:
        client.create_bucket(Bucket=name)
    except ClientError as create_exc:
        ccode = (create_exc.response.get("Error") or {}).get("Code", "")
        if ccode in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            return
        raise


def clear_s3_client_cache() -> None:
    """Test helper: reset LRU client cache."""

    _cached_client.cache_clear()
