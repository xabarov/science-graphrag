"""Opt-in live MinIO/S3 probe (not moto).

Set ``SCIENCE_GRAPHRAG_MINIO_E2E=1`` and the same S3 env as production
(``SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED``, endpoint, keys, bucket).

Typical local compose::

  export SCIENCE_GRAPHRAG_MINIO_E2E=1
  export SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED=true
  export SCIENCE_GRAPHRAG_S3_ENDPOINT_URL=http://localhost:19000
  export SCIENCE_GRAPHRAG_S3_USE_SSL=false
  .venv/bin/pytest tests/integration/test_minio_object_storage_e2e.py -q
"""

from __future__ import annotations

import os
import uuid

import pytest

from science_graphrag.config import Settings
from science_graphrag.storage.object_keys import ingest_queue_object_key
from science_graphrag.storage.s3_client import build_s3_client, clear_s3_client_cache

pytestmark = pytest.mark.minio_e2e


def _minio_e2e_enabled() -> bool:
    v = os.environ.get("SCIENCE_GRAPHRAG_MINIO_E2E", "").strip().lower()
    return v in ("1", "true", "yes", "on")


@pytest.mark.skipif(not _minio_e2e_enabled(), reason="SCIENCE_GRAPHRAG_MINIO_E2E not enabled")
def test_put_get_delete_ingest_queue_style_key() -> None:
    """Round-trip one small object under the ingest-queue key layout."""
    clear_s3_client_cache()
    try:
        settings = Settings()
        if not settings.object_storage_enabled:
            pytest.skip("SCIENCE_GRAPHRAG_OBJECT_STORAGE_ENABLED=false")
        client = build_s3_client(settings)
        bucket = (settings.s3_bucket or "").strip()
        if not bucket:
            pytest.skip("s3_bucket empty")

        jid = f"e2e-{uuid.uuid4().hex[:16]}"
        key = ingest_queue_object_key(jid, "probe.txt")
        body = b"science-graphrag-minio-e2e"

        client.put_object(Bucket=bucket, Key=key, Body=body)
        head = client.head_object(Bucket=bucket, Key=key)
        assert int(head["ContentLength"]) == len(body)
        resp = client.get_object(Bucket=bucket, Key=key)
        assert resp["Body"].read() == body
        client.delete_object(Bucket=bucket, Key=key)
    finally:
        clear_s3_client_cache()
