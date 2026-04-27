"""Ingest artifact store: local disk or S3/MinIO with optional mirror under ``artifact_root``."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any

from botocore.exceptions import ClientError

from science_graphrag.artifacts.local_store import LocalFilesystemArtifactStore
from science_graphrag.artifacts.protocols import ArtifactStorePort
from science_graphrag.config import Settings
from science_graphrag.storage.object_keys import (
    ingest_artifact_object_key,
    relative_artifact_from_object_key,
)


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _is_not_found(exc: ClientError) -> bool:
    code = _client_error_code(exc)
    return code in ("404", "NotFound", "NoSuchKey", "NoSuchBucket")


def _listing_prefix_for_pattern(pattern: str, *, s3_prefix: str) -> str:
    """S3 list prefix derived from glob pattern (first path segment containing wildcards)."""
    parts = pattern.split("/")
    idx = next(
        (i for i, p in enumerate(parts) if any(c in p for c in "*?[")),
        len(parts),
    )
    fixed_parts = parts[:idx]
    fixed = "/".join(fixed_parts)
    base = s3_prefix.strip().strip("/")
    if not fixed:
        return f"{base}/"
    if idx >= len(parts):
        return f"{base}/{fixed}"
    return f"{base}/{fixed}/"


class S3ArtifactStore:
    """
    Persist ingest artifacts in S3; mirror reads/writes to ``artifact_root`` for local cache.

    Reads prefer on-disk mirror when present; otherwise download from S3 and refresh mirror.
    ``glob_under`` / ``glob_under_entries`` merge local tree and S3 listings (migration-safe).
    """

    def __init__(self, client: Any, bucket: str, artifact_root: Path, key_prefix: str) -> None:
        """
        Wire boto client, bucket, local mirror root, and logical key prefix (e.g.
        ``science-artifacts``).
        """
        self._client = client
        self._bucket = bucket
        self._root = Path(artifact_root)
        self._key_prefix = key_prefix.strip().strip("/")
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        """Local mirror / cache directory (``Settings.artifact_root``)."""
        return self._root

    def _object_key(self, relative: Path) -> str:
        """Full S3 key for a path relative to the artifact root."""
        return ingest_artifact_object_key(relative, prefix=self._key_prefix)

    def _local_path(self, relative: Path) -> Path:
        """Absolute path under the local mirror tree."""
        return self._root / relative

    def absolute(self, relative: Path) -> Path:
        """Same as ``_local_path`` (``ArtifactStorePort`` contract)."""
        return self._local_path(relative)

    def write_text(
        self,
        relative: Path,
        text: str,
        *,
        encoding: str = "utf-8",
    ) -> Path:
        """Upload UTF-8 text to S3 and write the same bytes to the local mirror."""
        data = text.encode(encoding)
        key = self._object_key(relative)
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)
        path = self._local_path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return path

    def read_text(
        self,
        relative: Path,
        *,
        encoding: str = "utf-8",
        errors: str | None = None,
    ) -> str:
        """Read from local mirror if present; else fetch from S3 and refresh mirror."""
        path = self._local_path(relative)
        if path.is_file():
            return path.read_text(encoding=encoding, errors=errors or "strict")
        key = self._object_key(relative)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(
                    f"artifact not in S3 or local mirror: {relative.as_posix()} "
                    f"(bucket={self._bucket}, key={key!r})"
                ) from exc
            raise
        raw = resp["Body"].read()
        text = raw.decode(encoding, errors=errors or "strict")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        return text

    def exists(self, relative: Path) -> bool:
        """True if the object exists on disk or in S3."""
        if self._local_path(relative).is_file():
            return True
        key = self._object_key(relative)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _is_not_found(exc):
                return False
            raise
        return True

    def stat_st_size(self, relative: Path) -> int:
        """File size from local mirror or S3 ``ContentLength``."""
        path = self._local_path(relative)
        if path.is_file():
            return int(path.stat().st_size)
        key = self._object_key(relative)
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(
                    f"artifact not in S3 or local mirror: {relative.as_posix()} "
                    f"(bucket={self._bucket}, key={key!r})"
                ) from exc
            raise
        return int(resp["ContentLength"])

    def glob_under_entries(self, pattern: str) -> list[tuple[Path, float]]:
        """Merge local ``Path.glob`` matches with S3 keys under a derived list prefix."""
        by_key: dict[str, tuple[Path, float]] = {}
        for path in self._root.glob(pattern):
            if path.is_file():
                rel = path.relative_to(self._root)
                by_key[rel.as_posix()] = (rel, path.stat().st_mtime)
        list_prefix = _listing_prefix_for_pattern(pattern, s3_prefix=self._key_prefix)
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=list_prefix):
            for obj in page.get("Contents") or []:
                key = obj["Key"]
                rel = relative_artifact_from_object_key(key, prefix=self._key_prefix)
                if rel is None:
                    continue
                posix = rel.as_posix()
                if not PurePosixPath(posix).match(pattern):
                    continue
                ts = float(obj["LastModified"].timestamp())
                prev = by_key.get(posix)
                if prev is None or ts >= prev[1]:
                    by_key[posix] = (rel, ts)
        return list(by_key.values())

    def glob_under(self, pattern: str) -> list[Path]:
        """Absolute paths for each ``glob_under_entries`` match."""
        return [self.absolute(rel) for rel, _ in self.glob_under_entries(pattern)]

    def close(self) -> None:
        """Registry compat (no-op)."""
        return None


def build_artifact_store(settings: Settings) -> ArtifactStorePort:
    """
    Local filesystem or S3-backed ingest artifacts (Phase 2).

    Uses the same bucket as Phase 1 raw/queue; artifact keys use ``s3_artifact_key_prefix``.
    """
    if settings.object_storage_enabled:
        from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
            build_s3_client,
            ensure_bucket_exists,
        )

        client = build_s3_client(settings)
        ensure_bucket_exists(settings, client=client)
        return S3ArtifactStore(
            client,
            settings.s3_bucket,
            settings.artifact_root,
            settings.s3_artifact_key_prefix,
        )
    return LocalFilesystemArtifactStore(settings.artifact_root)
