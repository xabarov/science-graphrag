"""Phase 4: moto tests for tags, evidence zip, GC dry-run."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError

pytest.importorskip("moto")

from moto import mock_aws

from science_graphrag.artifacts.diagnostic_object_sink import write_diagnostic_json
from science_graphrag.config import Settings
from science_graphrag.storage.benchmark_run_persistence import S3BenchmarkRunPersistence
from science_graphrag.storage.evidence_bundle import (
    _safe_zip_entry_name,
    build_evidence_zip_bytes,
)
from science_graphrag.storage.object_storage_gc import (
    delete_object_keys,
    fix_summaries_after_benchmark_key_delete,
    iter_objects_older_than,
)
from science_graphrag.storage.s3_client import clear_s3_client_cache


def _os_settings(**kwargs: object) -> Settings:
    """Minimal Settings for moto S3 tests."""
    return Settings(
        object_storage_enabled=True,
        s3_access_key_id="testing",
        s3_secret_access_key="testing",
        s3_bucket="science-raw",
        s3_endpoint_url=None,
        diagnostics_object_storage=True,
        object_storage_diagnostics_retention_days=14,
        object_storage_benchmark_full_retention_days=30,
        **kwargs,  # type: ignore[arg-type]
    )


@mock_aws
def test_diagnostic_s3_upload_has_retention_tags() -> None:
    """Diagnostic JSON upload sets S3 object tags."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    settings = _os_settings()
    out = write_diagnostic_json(
        "probe.json",
        {"x": 1},
        settings=settings,
        kind="od",
    )
    assert out.get("storage") == "s3"
    key = out["key"]
    tags = client.get_object_tagging(Bucket="science-raw", Key=key)
    tag_map = {t["Key"]: t["Value"] for t in tags.get("TagSet", [])}
    assert tag_map.get("retention_class") == "ephemeral_diagnostic"
    assert tag_map.get("diagnostic_kind") == "od"
    assert tag_map.get("retention_hint_days") == "14"
    clear_s3_client_cache()


@mock_aws
def test_benchmark_put_full_json_has_retention_tags() -> None:
    """Benchmark full.json upload sets retention tags."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    store = S3BenchmarkRunPersistence(
        client,
        "science-raw",
        "science-benchmarks",
        retention_hint_days=30,
    )
    rid = "00000000-0000-4000-8000-000000000099"
    key = store.put_full_json(rid, '{"run_id":"x"}')
    tags = client.get_object_tagging(Bucket="science-raw", Key=key)
    tag_map = {t["Key"]: t["Value"] for t in tags.get("TagSet", [])}
    assert tag_map.get("retention_class") == "benchmark_full_run"
    assert tag_map.get("run_id") == rid
    assert tag_map.get("retention_hint_days") == "30"
    clear_s3_client_cache()


@mock_aws
def test_evidence_bundle_zip_contains_keys() -> None:
    """Evidence zip lists downloaded object bodies."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    key = "science-diagnostics/od/sample.json"
    client.put_object(Bucket="science-raw", Key=key, Body=b'{"a":1}')
    z = build_evidence_zip_bytes(client, "science-raw", [key])
    with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
        names = zf.namelist()
        assert key in names
        assert json.loads(zf.read(key).decode("utf-8")) == {"a": 1}
    clear_s3_client_cache()


@mock_aws
def test_gc_dry_run_iter_does_not_delete_without_caller() -> None:
    """Iterator finds old keys; empty delete batch leaves object in place."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    old_key = "science-diagnostics/od/old.json"
    client.put_object(Bucket="science-raw", Key=old_key, Body=b"{}")
    # Negative days marks all objects as past cutoff (test-only).
    found = list(
        iter_objects_older_than(
            client,
            "science-raw",
            "science-diagnostics/",
            older_than_days=-1.0,
        )
    )
    keys = [f.key for f in found]
    assert old_key in keys
    # dry-run path in real script does not call delete; ensure object still exists
    assert delete_object_keys(client, "science-raw", []) == []
    client.head_object(Bucket="science-raw", Key=old_key)
    clear_s3_client_cache()


@mock_aws
def test_gc_execute_removes_object() -> None:
    """delete_object_keys removes the object from the bucket."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    key = "science-diagnostics/eval/x.json"
    client.put_object(Bucket="science-raw", Key=key, Body=b"{}")
    found = [
        f.key
        for f in iter_objects_older_than(
            client, "science-raw", "science-diagnostics/", older_than_days=-1.0
        )
    ]
    assert key in found
    assert delete_object_keys(client, "science-raw", [key]) == []
    with pytest.raises(ClientError) as excinfo:
        client.head_object(Bucket="science-raw", Key=key)
    assert excinfo.value.response["Error"]["Code"] == "404"
    clear_s3_client_cache()


def test_safe_zip_entry_name_normalizes_dotdot() -> None:
    """Archive paths must not retain parent-directory segments."""
    assert _safe_zip_entry_name("a/../../b/x.json") == "a/b/x.json"
    assert _safe_zip_entry_name("evil/.././../etc/passwd") == "evil/etc/passwd"


@mock_aws
def test_evidence_bundle_uses_safe_archive_paths() -> None:
    """Keys with ``..`` segments map to a flat safe path inside the zip."""
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    key = "science-diagnostics/od/../od/nested.json"
    client.put_object(Bucket="science-raw", Key=key, Body=b"{}")
    z = build_evidence_zip_bytes(client, "science-raw", [key])
    with zipfile.ZipFile(io.BytesIO(z), "r") as zf:
        assert "science-diagnostics/od/od/nested.json" in zf.namelist()
    clear_s3_client_cache()


def test_fix_summaries_clears_deleted_key(tmp_path: Path) -> None:
    """Summary sidecar loses full_run_object_key when remote key was GC'd."""
    key = "science-benchmarks/runs/r1/full.json"
    p = tmp_path / "r1.summary.json"
    p.write_text(
        json.dumps({"run_id": "r1", "full_run_object_key": key, "full_run_json_bytes": 99}),
        encoding="utf-8",
    )
    n = fix_summaries_after_benchmark_key_delete(tmp_path, {key})
    assert n == 1
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["full_run_object_key"] is None
    assert data["full_run_json_bytes"] is None
