# Mandatory S3/MinIO — migration order

Object storage (S3-compatible, e.g. MinIO) is **required** for ingest queue payloads, content-addressed raw blobs, ingest artifacts, UI benchmark full JSON, and diagnostic sinks. Postgres/Neo4j/Qdrant still hold structured state and workspace metadata.

## Preconditions

1. MinIO (or AWS S3) reachable; credentials with write access to the target bucket.
2. Environment from repo root (see `.env.example`):
   - `SCIENCE_GRAPHRAG_S3_ENDPOINT_URL` (e.g. `http://localhost:19000` for compose MinIO on the host)
   - `SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID` / `SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY`
   - `SCIENCE_GRAPHRAG_S3_BUCKET` (e.g. `science-raw`)
   - `SCIENCE_GRAPHRAG_S3_USE_SSL=false` for plain HTTP MinIO in dev
   - `SCIENCE_GRAPHRAG_S3_ADDRESSING_STYLE=path` for MinIO
3. **Back up** Postgres, Neo4j, Qdrant volumes and the MinIO bucket before bulk migration.

## Recommended upload order

1. **Ingest artifacts** (`artifact_root` → keys under `SCIENCE_GRAPHRAG_S3_ARTIFACT_KEY_PREFIX`, default `science-artifacts`):

   ```bash
   .venv/bin/python scripts/sync_local_artifacts_to_s3.py --dry-run
   .venv/bin/python scripts/sync_local_artifacts_to_s3.py
   ```

2. **Raw blobs** (`blob_root/raw/ab/sha256` → `blobs/raw/ab/sha256`):

   ```bash
   .venv/bin/python scripts/sync_local_raw_blobs_to_s3.py --dry-run
   .venv/bin/python scripts/sync_local_raw_blobs_to_s3.py
   ```

3. **Benchmark full JSON** (optional if you use UI benchmark history with payloads under `data/benchmark_runs/`):

   ```bash
   .venv/bin/python scripts/sync_benchmark_runs_to_s3.py --dry-run
   .venv/bin/python scripts/sync_benchmark_runs_to_s3.py
   ```

4. Deploy API/worker with the **same** bucket and prefixes; run `science-graphrag config-check` (with S3 preflight as documented in CLI help).

## Legacy ingest jobs (Postgres)

Jobs created before queue objects lived in S3 may have an empty `queued_source_object_key` and only a file under `blob_root/_ingest_queue/`. The worker still supports that legacy path when the key is unset.

Options:

- **Re-enqueue** the document/workspace ingest after migration, or
- One-off: upload the queue file to `ingest-queue/{job_id}{suffix}`, then update the job row with `queued_source_object_key` (operator SQL/script — not shipped as a mandatory tool).

## Local mirror vs source of truth

`S3ArtifactStore` and `S3RawBlobStore` may still write a **local mirror** under `artifact_root` / `blob_root` for performance. The **authoritative** copy for multi-host operation is the object in the bucket; keep bucket backups independent of host disk.

## Smoke

See [object-storage-phase1-2-smoke.md](object-storage-phase1-2-smoke.md) and optional live MinIO tests in `tests/integration/test_minio_object_storage_e2e.py`.
