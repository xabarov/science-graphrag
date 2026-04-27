"""Benchmark UI run full JSON persistence: local disk or S3/MinIO (Phase 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from botocore.exceptions import ClientError

from science_graphrag.artifacts.retention import RetentionClass, s3_put_object_retention_kwargs
from science_graphrag.config import Settings
from science_graphrag.storage.benchmark_object_keys import benchmark_run_full_object_key


def _client_error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _is_not_found(exc: ClientError) -> bool:
    code = _client_error_code(exc)
    return code in ("404", "NotFound", "NoSuchKey", "NoSuchBucket")


class BenchmarkRunPersistencePort(Protocol):
    """Write/read full benchmark run JSON snapshots (not summaries)."""

    @property
    def remote_full_payloads(self) -> bool:
        """When true, full JSON is off-host (S3); summaries stay on local disk."""

    def put_full_json(self, run_id: str, json_text: str) -> str | None:
        """Persist UTF-8 JSON; returns object key when remote, else None (local file)."""

    def get_full_json(self, run_id: str, *, object_key: str | None = None) -> str | None:
        """Load full JSON text or None if missing."""

    def delete_full_json(self, run_id: str, *, object_key: str | None = None) -> None:
        """Best-effort removal of full payload (local file and/or S3)."""


class LocalBenchmarkRunPersistence:
    """Full run JSON under ``history_dir`` (legacy Phase 0–2 layout)."""

    def __init__(self, history_dir: Path) -> None:
        self._dir = Path(history_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def remote_full_payloads(self) -> bool:
        """Full JSON is stored on the API host under ``history_dir``."""
        return False

    def put_full_json(self, run_id: str, json_text: str) -> str | None:
        """Write ``<run_id>.json``; returns None (local path is conventional, not an S3 key)."""
        path = self._dir / f"{run_id}.json"
        path.write_text(json_text, encoding="utf-8")

    def get_full_json(self, run_id: str, *, object_key: str | None = None) -> str | None:
        """Read full JSON from disk; ``object_key`` is ignored for local layout."""
        del object_key
        path = self._dir / f"{run_id}.json"
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def delete_full_json(self, run_id: str, *, object_key: str | None = None) -> None:
        """Remove local ``<run_id>.json`` if present."""
        del object_key
        path = self._dir / f"{run_id}.json"
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass

    def close(self) -> None:
        """No-op for ``StoreRegistry.close``."""


class S3BenchmarkRunPersistence:
    """Full run JSON in S3; summaries remain local (written by task_store)."""

    def __init__(
        self,
        client: Any,
        bucket: str,
        key_prefix: str,
        *,
        retention_hint_days: int | None = None,
    ) -> None:
        self._client = client
        self._bucket = (bucket or "").strip()
        self._prefix = (key_prefix or "").strip().strip("/")
        self._retention_hint_days = retention_hint_days

    @property
    def remote_full_payloads(self) -> bool:
        """Full JSON lives in S3 under ``key_prefix``."""
        return True

    def _key(self, run_id: str) -> str:
        """S3 object key for the full run JSON."""
        return benchmark_run_full_object_key(run_id, prefix=self._prefix)

    def put_full_json(self, run_id: str, json_text: str) -> str | None:
        """Upload UTF-8 JSON; returns the object key."""
        key = self._key(run_id)
        extra = s3_put_object_retention_kwargs(
            RetentionClass.BENCHMARK_FULL_RUN,
            run_id=run_id,
            retention_hint_days=self._retention_hint_days,
        )
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json_text.encode("utf-8"),
            ContentType="application/json",
            **extra,
        )
        return key

    def get_full_json(self, run_id: str, *, object_key: str | None = None) -> str | None:
        """Download object body as UTF-8 text."""
        key = (object_key or "").strip() or self._key(run_id)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read().decode("utf-8")
        except ClientError as exc:
            if _is_not_found(exc):
                return None
            raise

    def delete_full_json(self, run_id: str, *, object_key: str | None = None) -> None:
        """Best-effort ``delete_object`` (ignores missing key)."""
        key = (object_key or "").strip() or self._key(run_id)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError:
            pass

    def close(self) -> None:
        """No-op for ``StoreRegistry.close``."""


def build_benchmark_run_persistence(
    settings: Settings, history_dir: Path
) -> BenchmarkRunPersistencePort:
    """Local persistence by default; S3 when ``benchmark_runs_object_storage`` is enabled."""

    hist = Path(history_dir)
    if getattr(settings, "benchmark_runs_object_storage", False):
        from science_graphrag.storage.s3_client import (  # pylint: disable=import-outside-toplevel
            build_s3_client,
            ensure_bucket_exists,
        )

        client = build_s3_client(settings)
        ensure_bucket_exists(settings, client=client)
        prefix = (
            getattr(settings, "s3_benchmark_runs_key_prefix", None) or "science-benchmarks"
        ).strip()
        hint = int(getattr(settings, "object_storage_benchmark_full_retention_days", 0) or 0)
        return S3BenchmarkRunPersistence(
            client,
            settings.s3_bucket,
            prefix,
            retention_hint_days=hint if hint > 0 else None,
        )
    return LocalBenchmarkRunPersistence(hist)
