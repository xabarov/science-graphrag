"""S3-backed stores with moto (no real MinIO required)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("moto")

from moto import mock_aws

from science_graphrag.config import Settings
from science_graphrag.storage.ingest_queue_store import S3IngestQueueStore
from science_graphrag.storage.raw_blob_store import S3RawBlobStore
from science_graphrag.storage.s3_client import clear_s3_client_cache


@pytest.fixture(autouse=True)
def _clear_s3_cache() -> None:
    clear_s3_client_cache()
    yield
    clear_s3_client_cache()


@mock_aws
def test_s3_ingest_queue_roundtrip(tmp_path: Path) -> None:
    import boto3

    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="science-raw")
    store = S3IngestQueueStore(conn, "science-raw")
    key = store.put("j1", "a.pdf", b"abc")
    out = tmp_path / "downloaded.pdf"
    store.get_to_path(key, out)
    assert out.read_bytes() == b"abc"
    store.delete(key)


@mock_aws
def test_s3_raw_blob_store_roundtrip(tmp_path: Path) -> None:
    import boto3

    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="science-raw")
    root = tmp_path / "blobs"
    root.mkdir()
    src = tmp_path / "source.txt"
    src.write_bytes(b"payload-bytes")
    store = S3RawBlobStore(conn, "science-raw", root)
    sha, returned = store.store_file(src)
    assert returned == src
    assert len(sha) == 64
    p = store.path_for_sha(sha)
    assert p.is_file()
    assert p.read_bytes() == b"payload-bytes"


@mock_aws
def test_build_stores_from_settings(tmp_path: Path) -> None:
    import boto3

    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="science-raw")
    clear_s3_client_cache()
    settings = Settings(
        object_storage_enabled=True,
        s3_endpoint_url=None,
        s3_access_key_id="testing",
        s3_secret_access_key="testing",
        s3_bucket="science-raw",
        s3_use_ssl=True,
        blob_root=tmp_path / "blobs",
        artifact_root=tmp_path / "artifacts",
    )
    from science_graphrag.storage.ingest_queue_store import build_ingest_queue_store
    from science_graphrag.storage.raw_blob_store import build_raw_blob_store

    q = build_ingest_queue_store(settings)
    key = q.put("jid", "f.md", b"x")
    dest = tmp_path / "d.md"
    q.get_to_path(key, dest)
    assert dest.read_bytes() == b"x"

    r = build_raw_blob_store(settings)
    f = tmp_path / "u.txt"
    f.write_text("ok", encoding="utf-8")
    sha, _ = r.store_file(f)
    assert r.path_for_sha(sha).read_bytes() == b"ok"
