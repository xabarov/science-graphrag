# ADR 025: Mandatory S3-compatible object storage

**Status:** accepted (2026-04-28)

## Context

Ingest queue payloads, content-addressed raw blobs, ingest artifacts (`article.md`, `normalized.md`, diagnostics), UI benchmark full JSON, and CLI diagnostic sinks previously toggled via `object_storage_enabled`, `benchmark_runs_object_storage`, and `diagnostics_object_storage`. Local `Local*` store implementations remained selectable, which complicated multi-host deployments and operator mental models.

## Decision

1. **Require** non-empty `SCIENCE_GRAPHRAG_S3_ACCESS_KEY_ID`, `SCIENCE_GRAPHRAG_S3_SECRET_ACCESS_KEY`, and `SCIENCE_GRAPHRAG_S3_BUCKET` for every `Settings()` construction (validated in `science_graphrag/config.py`).
2. **Production factories** `build_ingest_queue_store`, `build_raw_blob_store`, `build_artifact_store`, and `build_benchmark_run_persistence` always use S3-backed implementations (`S3IngestQueueStore`, `S3RawBlobStore`, `S3ArtifactStore`, `S3BenchmarkRunPersistence`). Local implementations remain in the codebase for focused unit tests and legacy worker paths (empty `queued_source_object_key`).
3. **`diagnostic_object_sink`** always writes diagnostics to the configured bucket under `s3_diagnostics_key_prefix`.
4. **UI / API** no longer expose toggles for the removed flags; settings schema version bumped to **10**.
5. **Module-level `task_store`** still defaults to `LocalBenchmarkRunPersistence` at import so test collection does not call live S3; the FastAPI lifespan attaches `StoreRegistry.benchmark_runs` (S3) via `attach_benchmark_run_persistence` before serving traffic.

## Consequences

- **Developers and CI** must provide S3 credentials (see `tests/conftest.py` defaults for pytest; use MinIO from compose or moto for unit tests).
- **Migration** from disk-only installs: [`docs/runbooks/mandatory-s3-migration.md`](../runbooks/mandatory-s3-migration.md) and `scripts/sync_local_raw_blobs_to_s3.py`.
- **Air-gapped `config-check`:** use `--no-object-storage-preflight` if the process must not contact S3 at startup diagnostics.

## Related

- [`docs/analysis/minio-integration-and-artifact-storage-roadmap-2026-04-27.md`](../analysis/minio-integration-and-artifact-storage-roadmap-2026-04-27.md) §8 Phase 3 note
- [`docs/adr/024-artifact-promotion-and-retention-phase4.md`](024-artifact-promotion-and-retention-phase4.md)
