# Object storage Phase 1–2 — smoke checklist

Use this to validate **multi-host ingest** and **S3-backed artifacts** against a real MinIO (or AWS S3) before treating Phase 1–2 as production-ready.

## Preconditions

1. **MinIO (or S3)** reachable; bucket exists or API may create it (`ensure_bucket_exists`).
2. **Environment** (from repo root, see `.env.example`):

   - `SCIENCE_GRAPHRAG_S3_ENDPOINT_URL` (e.g. `http://localhost:19000` for compose MinIO)
   - `SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID` / `SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY`
   - `SCIENCE_GRAPHRAG_S3_BUCKET=science-raw` (or your bucket)
   - `SCIENCE_GRAPHRAG_S3_USE_SSL=false` when using plain HTTP MinIO in dev
   - `SCIENCE_GRAPHRAG_S3_ADDRESSING_STYLE=path` for MinIO

3. **Postgres + worker + API** healthy if you run end-to-end ingest (not required for boto-only checks).

## Phase 1 — ingest queue + raw blobs

**Code:** `build_ingest_queue_store` → [`science_graphrag/storage/ingest_queue_store.py`](../../science_graphrag/storage/ingest_queue_store.py); worker uses `job.queued_source_object_key` in [`science_graphrag/worker/actor.py`](../../science_graphrag/worker/actor.py); dispatcher persists via [`science_graphrag/api/ingest/dispatcher.py`](../../science_graphrag/api/ingest/dispatcher.py). Raw blobs: [`science_graphrag/storage/raw_blob_store.py`](../../science_graphrag/storage/raw_blob_store.py).

**Checks:**

1. **Unit-level (CI):** `pytest tests/storage/test_object_storage_moto.py::test_s3_ingest_queue_roundtrip` and `test_s3_raw_blob_store_roundtrip` pass with `moto`.
2. **Manual:** enqueue a small PDF ingest with object storage on; confirm Postgres job row has non-empty `queued_source_object_key`; confirm worker completes and object appears under logical prefix `ingest-queue/` in the bucket (MinIO console or `mc ls`).
3. **Two-host mental model:** API host only needs S3 credentials + DB; worker host needs the same — **no** shared `blob_root/_ingest_queue` for new jobs (legacy path remains only when `queued_source_object_key` is null).

## Phase 2 — ingest artifacts (`artifact_root` seam)

**Code:** [`science_graphrag/storage/s3_artifact_store.py`](../../science_graphrag/storage/s3_artifact_store.py) (`S3ArtifactStore` + local mirror), `build_artifact_store` from [`science_graphrag/api/deps.py`](../../science_graphrag/api/deps.py); pipeline and reader paths use the same seam ([`science_graphrag/ingestion/_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py), [`science_graphrag/api/works/detail.py`](../../science_graphrag/api/works/detail.py)).

**Checks:**

1. **Unit-level:** `pytest tests/storage/test_object_storage_moto.py::test_s3_artifact_store_read_stat_without_local_mirror` — proves read after deleting on-disk mirror still works from S3.
2. **Manual:** after ingest, verify keys under `SCIENCE_GRAPHRAG_S3_ARTIFACT_KEY_PREFIX` (default `science-artifacts`) for `ingestion/<document_id>/…`; open extracted-body API for that document from a **second** process/machine with empty local mirror (or delete mirror files) and confirm content loads.

## Automated MinIO probe (optional)

With `SCIENCE_GRAPHRAG_MINIO_E2E=1` and the same S3 env as above:

```bash
.venv/bin/pytest tests/integration/test_minio_object_storage_e2e.py -q -m minio_e2e
```

Tests are marked `minio_e2e` and skip unless the env flag is set (see module docstring).
