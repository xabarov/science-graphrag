# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Queue

### [DONE] Graph readability — Wave GR1 display labels (Authorship/Author/Institution/Venue)
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Graph projections leaked technical UUID-like node ids (notably `:Authorship` ids like `...:ash:1`) into `display_label`/`subtitle`, reducing readability.
- **Proposal:** Introduce shared display helper and enrich Authorship labels from `OF_AUTHOR`/`AFFILIATED_WITH`; apply in all graph endpoints.
- **Acceptance:** no UUID-like labels in graph node titles/subtitles for core node types; integration + unit tests cover Authorship rendering.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — implemented in GR1 pass with tests for `/v1/works/{id}/graph`, `/v1/workspaces/{id}/graph`, and `/v1/workspaces/{id}/graph/neighbors`.

### [OPEN] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** `node_kind` is still equal to Neo4j `type`; edge labels remain technical (`HAS_AUTHORSHIP`, etc.); `LIMIT` truncation is not priority-aware.
- **Proposal:** Add `node_kind` projection semantics, relation `display_type` mapping, and limit prioritization with `meta.skipped_by_kind`.
- **Acceptance:** priority kinds (`Method`,`Dataset`,`Work`) survive truncation reliably and UI legend can render semantic edge labels.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR3 aggregator nodes + lazy expand endpoint
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Dense one-kind neighbor stars (authors/cites/institutions) overload graph readability at default limits.
- **Proposal:** Add `node_kind: Aggregator` projection with `aggregation_hints` and expand endpoint for lazy unfolding.
- **Acceptance:** oversized neighbor groups collapse into one aggregator node with count/preview and expand on demand.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR4 reader view with virtual AUTHORED edges
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`, `science_graphrag/api/graph_snapshot_diff.py`
- **Issue:** Raw `Authorship` reification is useful for ontology/debug but too verbose for default reader UX.
- **Proposal:** Add `view=raw|reader`; in reader view project virtual `AUTHORED` edges with `via` trace fields, keep raw mode for snapshots/tests.
- **Acceptance:** reader view hides `Authorship` nodes by default while preserving traceability and raw compatibility.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR5 denormalized Work counters for weighted layout
- **Area:** `science_graphrag/storage/neo4j_store.py`, ingestion pipelines, graph API payload properties
- **Issue:** Work importance signals (`cites_in/out`, `authors_count`) are recomputed ad hoc and not consistently available for graph styling.
- **Proposal:** Persist denormalized counters on `:Work` and expose them in graph payload properties.
- **Acceptance:** graph payload includes stable counter properties enabling weighted radius/ranking without extra query passes.
- **Raised:** 2026-04-25

### [PARTIAL] Ingest pipeline async-redesign (Wave U–W)

- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/ingestion/pipeline.py`, `ui/src/hooks/usePollJob.js`, `docker/nginx-web.conf`, `docker-compose.yml`
- **Issue:** ingest исполняется `threading.Thread` внутри API → рестарт убивает работу; UI поллит `GET /v1/ingest/jobs/{id}` каждые 2 с → access-лог зашумлён; пайплайн не размечен на стадии → видимость нулевая (`message: "Running pipeline (Neo4j / vectors / SQL)…"` минутами).
- **Proposal:** план в [docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md](../analysis/ingestion-async-pipeline-roadmap-2026-04-25.md):
  - **Wave U** — фильтр polling из uvicorn access-лога; ORM `IngestJobStageOrm` + enum `IngestStage`; контекст-менеджер `stage(...)` с OTel-спанами; UI `IngestStageStepper`.
  - **Wave V** — `sse-starlette` + `GET /v1/ingest/jobs/{id}/events` с `Last-Event-ID`; nginx SSE-friendly `location`; UI `useJobStream` с graceful fallback на polling.
  - **Wave W** — ADR + `redis` и `worker` в compose; `dramatiq` actor `ingest_document_actor`; API только enqueue; `IngestEventBus` v2 поверх Redis pub/sub; идемпотентность + compensation sweep; `mark_stale_running_jobs_failed` удаляется.
- **Acceptance:** см. чеклисты Wave U/V/W в роадмапе. Закрывается тремя независимыми проходами; до Wave W можно держать `[PARTIAL]` после прохождения U или V.
- **Raised:** 2026-04-25
- **Note (Wave U done):** 2026-04-25 — stage timeline, OTel stage spans, `IngestStageStepper`, и filtering polling access-log доставлены; Wave V/W остаются открытыми.

### [OPEN] Split idea-assist workflow orchestration (Wave S follow-up)
- **Area:** `science_graphrag/agent/idea_workflow.py`
- **Issue:** `idea_workflow.py` reached ~270 lines and now mixes retrieval orchestration, claim querying, LLM prompting, and output normalization in one module.
- **Proposal:** Extract (1) claim/context collector, (2) LLM schema+prompt builder, and (3) result normalizer into separate modules under `science_graphrag/agent/idea_assist/`.
- **Acceptance:** orchestrator file <= 180 lines, prompt/schema logic isolated, and unit tests target each submodule independently.
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
