# Ingest job progress API (canonical fields)

## Purpose

`GET /v1/ingest/jobs/{job_id}` and the initial SSE `snapshot` return a **single canonical progress model** so the UI does not re-derive phases from ad-hoc rules.

## Top-level fields (job object)

| Field | Type | Description |
|-------|------|-------------|
| `progress_pct` | `number \| null` | Overall completion **0..1**. Weighted by historical stage durations; the active `running` stage can refine weight using `subprogress_*`. |
| `ingest_phase` | `string` | One of: `preparing_document`, `building_graph`, `preparing_search`, `finalizing`. |
| `active_stage` | `string` | Technical stage id (e.g. `parse_pdf`, `extract_claims`). Empty when unknown / idle. |
| `detail_message` | `string \| null` | Short human-oriented status (English), e.g. `PDF pages 3/10`. |
| `subprogress_current` | `int \| null` | Optional counter inside the active heavy stage. |
| `subprogress_total` | `int \| null` | Denominator for `subprogress_current`. |

Legacy fields `progress_current` / `progress_total` remain for backward compatibility (coarse worker checkpoints and batch file counts).

## Per-stage rows (`stages[]`)

Each stage includes:

- `name`, `status`, timestamps, `metrics`, `expected_duration_ms` (as before)
- `detail_message`, `subprogress_current`, `subprogress_total` when present (mirrored from `metrics` for the API view)

## SSE events

- `stage_started` / `stage_finished` / `stage_failed` — unchanged semantics.
- `stage_progress` — emitted while a stage is `running`; payload includes `stage`, `status: "running"`, and `metrics` (including `detail_message` / `subprogress_*` keys). Clients merge it into `stages[]` the same way as `stage_started`.

## Batch parent jobs

For `kind: "batch_parent"`, `child_jobs[]` contains full child job objects. The parent also receives:

- `progress_pct` — mean of child `progress_pct` when all children expose it; otherwise `done_children / total_children`.
- `ingest_phase`, `active_stage`, `detail_message`, `subprogress_*` — copied from the first `running` child, else first `queued` child; when all children are finished, `ingest_phase` is `finalizing`.

## Server modules

- Mapping & aggregation: `science_graphrag/api/ingest/ingest_progress.py`
- Weighted % with intra-stage fraction: `science_graphrag/ingestion/stage_stats.py` (`compute_weighted_progress_pct_with_running_fraction`)
- Mid-flight DB + SSE updates: `science_graphrag/ingestion/stage_context.py` (`StageHandle.flush_progress`, `patch_running_stage_metrics`)
