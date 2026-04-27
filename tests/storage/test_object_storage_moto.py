"""S3-backed stores with moto (no real MinIO required)."""

from __future__ import annotations

import pytest

pytest.importorskip("moto")

from pathlib import Path

from moto import mock_aws

from science_graphrag.config import Settings
from science_graphrag.storage.ingest_queue_store import S3IngestQueueStore
from science_graphrag.storage.object_keys import DEFAULT_S3_ARTIFACT_KEY_PREFIX
from science_graphrag.storage.raw_blob_store import S3RawBlobStore
from science_graphrag.storage.s3_artifact_store import S3ArtifactStore, build_artifact_store
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


@mock_aws
def test_s3_artifact_store_write_read_glob(tmp_path: Path) -> None:
    import boto3

    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="science-raw")
    art_root = tmp_path / "artifacts"
    store = S3ArtifactStore(conn, "science-raw", art_root, DEFAULT_S3_ARTIFACT_KEY_PREFIX)
    rel = Path("ingestion") / "doc1" / "slug-x" / "article.md"
    store.write_text(rel, "<!-- source=a.pdf extraction_mode=vl -->\n\n# Hi")
    assert store.exists(rel)
    assert "Hi" in store.read_text(rel)
    entries = sorted(
        store.glob_under_entries("ingestion/doc1/*/article.md"),
        key=lambda t: t[1],
        reverse=True,
    )
    assert len(entries) == 1
    assert entries[0][0] == rel


@mock_aws
def test_s3_artifact_store_read_stat_without_local_mirror(tmp_path: Path) -> None:
    """After removing the on-disk mirror, reads and sizes must still resolve from S3."""
    import boto3

    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="science-raw")
    art_root = tmp_path / "artifacts"
    store = S3ArtifactStore(conn, "science-raw", art_root, DEFAULT_S3_ARTIFACT_KEY_PREFIX)
    rel = Path("ingestion") / "doc2" / "normalized.md"
    payload = "only-in-s3\n"
    store.write_text(rel, payload)
    local = store.absolute(rel)
    assert local.is_file()
    local.unlink()
    assert not local.is_file()
    assert store.exists(rel)
    assert store.read_text(rel) == payload
    assert store.stat_st_size(rel) == len(payload.encode("utf-8"))


@mock_aws
def test_build_artifact_store_s3_writes_bucket(tmp_path: Path) -> None:
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
    store = build_artifact_store(settings)
    rel = Path("ingestion") / "d99" / "normalized.md"
    store.write_text(rel, "normalized-body")
    assert store.read_text(rel) == "normalized-body"
