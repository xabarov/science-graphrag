# Ingest Worker v1 (Wave W)

## Scope

Wave W moves ingest execution from API in-process threads to a dedicated Dramatiq worker.
API is responsible for job creation and enqueue only.

## Dramatiq queue and retry policy

- Actor: `ingest_document_actor`
- Queue: `ingest`
- Retries: `max_retries=2`
- Middleware:
  - `AgeLimit=3h`
  - `TimeLimit=1h`

## Message format

Worker messages carry only job id:

```json
{"job_id":"<uuid>"}
```

No payload with file bytes is sent through Redis queue.

## Input file handoff

API persists uploaded bytes to a shared queue path under `blob_root`:

- Single: `{blob_root}/_ingest_queue/{job_id}.{ext}`
- Batch child: same pattern per child job id

Worker resolves path from `job_id` and registry filename extension.

## Idempotency model

- If `job_id` is missing in registry, actor logs and exits.
- If job is already terminal (`completed`/`failed`), actor exits without rerun.
- Stage-level idempotency is preserved by existing stage context + registry updates.

## Compensation sweep

On worker startup, run compensation sweep:

- Query jobs where `status='queued'` and `created_at < now()-60s`.
- Re-enqueue each stale job id to `ingest_document_actor`.

Registry API: `list_stale_queued_jobs(before=...)`.

## IngestEventBus v2 contract

- Live channel format: `ingest:events:{job_id}` via Redis pub/sub.
- Event history/replay (`Last-Event-ID`) remains backed by Postgres `IngestJobEventOrm`.
- Retention cleanup target: 24h (`cleanup_old_events(ttl_hours=24)`).

## Operational notes

- Required env: `SCIENCE_GRAPHRAG_REDIS_URL`.
- Compose services: `redis`, `worker`, `api`.
- Worker process command: `python -m science_graphrag.worker`.
