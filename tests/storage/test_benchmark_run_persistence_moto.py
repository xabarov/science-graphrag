"""S3 benchmark run persistence (main-thread only; moto)."""

from __future__ import annotations

import pytest

pytest.importorskip("moto")

import boto3
from moto import mock_aws

from science_graphrag.storage.benchmark_run_persistence import S3BenchmarkRunPersistence
from science_graphrag.storage.s3_client import clear_s3_client_cache


@mock_aws
def test_s3_benchmark_run_put_get_roundtrip() -> None:
    clear_s3_client_cache()
    client = boto3.client("s3", region_name="us-east-1")
    client.create_bucket(Bucket="science-raw")
    store = S3BenchmarkRunPersistence(client, "science-raw", "science-benchmarks")
    rid = "00000000-0000-4000-8000-000000000001"
    body = '{"run_id":"%s","status":"completed"}' % rid
    key = store.put_full_json(rid, body)
    assert key.endswith("/full.json")
    assert store.get_full_json(rid, object_key=key) == body
    store.delete_full_json(rid, object_key=key)
    assert store.get_full_json(rid, object_key=key) is None
    clear_s3_client_cache()
