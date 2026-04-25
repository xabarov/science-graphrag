# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Queue

### [OPEN] Ingest pipeline async-redesign (Wave U–W)

- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/ingestion/pipeline.py`, `ui/src/hooks/usePollJob.js`, `docker/nginx-web.conf`, `docker-compose.yml`
- **Issue:** ingest исполняется `threading.Thread` внутри API → рестарт убивает работу; UI поллит `GET /v1/ingest/jobs/{id}` каждые 2 с → access-лог зашумлён; пайплайн не размечен на стадии → видимость нулевая (`message: "Running pipeline (Neo4j / vectors / SQL)…"` минутами).
- **Proposal:** план в [docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md](../analysis/ingestion-async-pipeline-roadmap-2026-04-25.md):
  - **Wave U** — фильтр polling из uvicorn access-лога; ORM `IngestJobStageOrm` + enum `IngestStage`; контекст-менеджер `stage(...)` с OTel-спанами; UI `IngestStageStepper`.
  - **Wave V** — `sse-starlette` + `GET /v1/ingest/jobs/{id}/events` с `Last-Event-ID`; nginx SSE-friendly `location`; UI `useJobStream` с graceful fallback на polling.
  - **Wave W** — ADR + `redis` и `worker` в compose; `dramatiq` actor `ingest_document_actor`; API только enqueue; `IngestEventBus` v2 поверх Redis pub/sub; идемпотентность + compensation sweep; `mark_stale_running_jobs_failed` удаляется.
- **Acceptance:** см. чеклисты Wave U/V/W в роадмапе. Закрывается тремя независимыми проходами; до Wave W можно держать `[PARTIAL]` после прохождения U или V.
- **Raised:** 2026-04-25

### [OPEN] DB-backed benchmark run store (deferred)

- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** File-backed snapshots suffice for single-host dev/QA; a DB would add ops cost without a clear trigger today.
- **Proposal:** Stay on disk until **multi-host** API or **large-volume** retained run history becomes a product requirement; then design migrations, retention, and export parity with current JSON snapshots.
- **Acceptance:** No DB migration started without an operational signal captured in a pilot/ops note; file-backed path remains documented as the default.
- **Raised:** 2026-04-19

<!-- Example:
### [OPEN] Example — tighten retrieval module boundaries
- **Area:** `science_graphrag/api/retrieval.py`, related services
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->

### [DONE] Audit teacher-gold benchmark fixtures
- **Area:** `eval/teacher_gold/layer1/`, generation scripts in `scripts/`, benchmark run persistence in `science_graphrag/api/benchmark.py`
- **Issue:** `teacher_gold` fixtures are partially sparse and can drift from curated gold or persisted run payloads; this creates false negatives in benchmark analysis and makes UI triage harder.
- **Proposal:** follow [benchmarks/teacher-gold-audit-v1.md](../benchmarks/teacher-gold-audit-v1.md): inventory fields, diff fixtures vs `data/benchmark_runs/*.json` gold payloads, triage, remediation.
- **Acceptance:** documented audit checklist, prioritized list of suspect cases, and an agreed remediation path for fixture refresh vs. post-processing repair.
- **Raised:** 2026-04-07
- **Note (done):** 2026-04-19 — Wave E1 baseline: [teacher-gold-audit-checklist.md](../benchmarks/teacher-gold-audit-checklist.md) extended with layer-2 table + **Audit exit** block; ongoing row-by-row review stays in that checklist until all phases CLOSED.

### [DONE] Durable benchmark run snapshots (UI API)
- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** Earlier bridge backlog called out “durable runs”; runs must survive API restart for dev/QA.
- **Proposal:** Implemented: `_persist_run_snapshot`, `_load_persisted_runs`, `.summary.json` sidecars; see `BenchmarkTaskStore` docstring.
- **Acceptance:** Restart API → run list/history still lists completed runs from disk; documented in Phase 6 bridge backlog.
- **Raised:** 2026-04-06
- **Note (done):** 2026-04-19 — backlog row closed; optional future work is DB-backed store if file volume becomes a bottleneck.
