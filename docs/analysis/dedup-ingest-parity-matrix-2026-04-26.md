# Dedup ingest parity matrix (2026-04-26)

Coverage of **near-duplicate review queues** by domain object, how conflicts are created, and where they surface.

| Kind | Scan (`origin=scan`) | Ingest (`origin=ingest`) | Backend queue table | Decide API | UI review |
|------|----------------------|---------------------------|---------------------|------------|-----------|
| **Work** | `POST /v1/workspaces/{id}/dedup/scan` → job | `enqueue_work_near_duplicate_conflicts_on_ingest` in `WRITE_GRAPH` (before `upsert_work_layer1`) | `work_dedup_conflicts` | `GET/POST .../dedup/conflicts` | `IngestConflictReviewCard` |
| **Author** | `POST .../dedup/authors/scan` → job | `enqueue_author_near_duplicate_conflicts_on_ingest` after semantic sync in `WRITE_GRAPH` | `author_dedup_conflicts` (+ `origin`) | `GET/POST .../dedup/authors/conflicts` | `AuthorConflictReviewCard` |
| **Entity** (institution, venue, method, dataset) | `POST /v1/dedup/entity/run` | `enqueue_entity_near_duplicate_conflicts_on_ingest` after semantic sync | `entity_dedup_conflicts` (+ `origin`) | `GET/POST /v1/dedup/entity` | `EntityConflictReviewCard` |

## Ingest job payload

`GET /v1/ingest/jobs/{job_id}` includes:

- `pending_conflicts`: `{ "works", "authors", "entities" }` — counts of **pending** rows with `origin=ingest` touching this job’s `work_id` (authors/entities resolved via Neo4j “on this work” id sets).
- `pending_conflicts_count`: sum of the three (backward compatible).

## Tests

| Area | Test file |
|------|-----------|
| Work ingest enqueue | `tests/test_ingest_conflict_check.py` |
| Author ingest enqueue | `tests/test_ingest_author_conflict_check.py` |
| Entity ingest enqueue | `tests/test_ingest_entity_conflict_check.py` |
| Job JSON `pending_conflicts` | `tests/test_api_smoke.py` (`test_get_ingest_job_includes_pending_conflicts_breakdown`) |

## Relation to osint-gr

osint-gr blocks persistence until conflicts are resolved (Redis task metadata + `resolve-conflicts`). science-graphrag uses a **post-hoc queue**: ingest completes; the workspace page shows review cards when `pending_conflicts` / prefetch detects pending ingest-origin rows.

## Migrations

- `20260426_0004`: `work_dedup_conflicts.origin`
- `20260426_0005`: `author_dedup_conflicts.origin`, `entity_dedup_conflicts.origin`
