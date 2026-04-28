# Logging system: deep dive and improvement plan

**Date:** 2026-04-28  
**Scope:** backend (`science_graphrag/`), Dramatiq worker, FastAPI (`uvicorn`), relation to Phoenix/OTel and ingest job observability.  
**Out of scope:** frontend `console` / Vite HMR logging (separate norms).

---

## 1. Executive summary

The project uses **Python stdlib `logging`** with a thin wrapper (`science_graphrag.utils.project_logging`) for part of the tree, while other modules use **`logging.getLogger(__name__)`** directly. **Uvicorn** and **third-party libraries** (`httpx`, Dramatiq, Phoenix registration) dominate **Docker stdout** at default levels: long ingest runs appear as **sparse or noisy** lines, while **structured progress** lives in **Postgres + SSE + Phoenix spans**, not in text logs.

**Main risks:** operator confusion (logs say little during VL PDF), duplicate/fragmented logger setup, and **job-table observability cost**: the `ingest_jobs.logs` column is **truncated per row** (~48k chars), but **rows accumulate** with no separate retention story here—still no grep-friendly link from stdout to that tail unless `job_id` appears in both (separate from stdlib logging but part of the “observability story”).

**Recommendation:** treat **logs, traces, and job artifacts** as one product surface: standardize **correlation IDs** (`job_id`, `workspace_id`), add **rate-limited INFO heartbeats** for long ingest steps, **tune third-party loggers** via env, and optionally adopt **JSON logs** behind a flag for production aggregation.

---

## 2. Current architecture

### 2.1 Project logging helper

**File:** `science_graphrag/utils/project_logging.py`

| Mechanism | Behavior |
|-----------|----------|
| `configure_logging()` | Idempotent: attaches **one** `StreamHandler(sys.stderr)` to logger `science_graphrag`, level from **`SCIENCE_GRAPHRAG_LOG_LEVEL`** (default `INFO`), format `%(asctime)s [%(levelname)s] %(name)s: %(message)s`. |
| `get_logger(name)` | Returns `science_graphrag.<name>` after calling `configure_logging()`. |

**Gaps (remaining):**

- Only the **`science_graphrag`** logger gets the handler; children propagate as before. **`configure_logging()`** is now invoked early in **FastAPI lifespan** (`api/main.py`), **worker** import (`worker/__init__.py`, `worker/actor.py`), and **CLI** — so API and worker processes align on formatter and `SCIENCE_GRAPHRAG_LOG_LEVEL` without waiting for the first `get_logger` call.
- **Optional:** `SCIENCE_GRAPHRAG_LOG_FORMAT=json` for aggregation (Phase 3). **Per-subsystem:** `SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST` overrides level for `science_graphrag.ingestion` only (see runbook).

### 2.2 Two logger acquisition patterns

**Pattern A — `get_logger("ingestion.pipeline")` (canonical for newer ingest/dedup):**  
Used in `_pipeline_impl`, dedup engines, `orchestrator`, `semantic_extraction`, `claims/extractor`, `resume_ingest`, etc. Names are **short aliases**, not full module paths.

**Pattern B — `logger = logging.getLogger(__name__)`:**  
Used in API (`agent_v2`, `task_store`, `idea_assist`), worker (`actor`, `__init__`, `otel_middleware`), storage, LLM concurrency, retrieval, agent session backend, etc.

**Consequence:** log line **names** remain inconsistent by choice (short aliases vs `__name__`). **Levels and formatter** for the `science_graphrag` tree are consistent in API and worker after the centralized `configure_logging()` calls above.

### 2.3 FastAPI / Uvicorn

**File:** `science_graphrag/api/main.py`

- **`_SuppressIngestPolling`:** drops **INFO** access lines that contain both `/v1/ingest/jobs/` and `" 200"` — reduces noise from UI polling.
- **Side effect:** successful ingest job polls leave **no** access trace at INFO (errors/non-200 still log).

Uvicorn default loggers (`uvicorn`, `uvicorn.access`, `uvicorn.error`) are **not** centrally configured in-repo; level is effectively environment + defaults.

### 2.4 Dramatiq worker

**File:** `science_graphrag/worker/__init__.py`

- Broker middleware: Retries, **AgeLimit**, **TimeLimit**, custom OTel middleware.
- **Startup:** `run_compensation_sweep()` logs at INFO; Dramatiq emits **one “ready” line per worker process** (high fanout with default process count).
- **Actor:** `ingest_document_actor` logs INFO at claim, skip paths, pipeline exit, and **terminal status** (after pipeline); `ingest_log_context` supplies `job_id` / `workspace_id` on stderr lines.

### 2.5 Ingestion pipeline (example signal density)

**File:** `science_graphrag/ingestion/_pipeline_impl.py`

- Logger: `get_logger("ingestion.pipeline")` → `science_graphrag.ingestion.pipeline`.
- **INFO:** cache reuse message, plus at least one other `log.info` path (batch/directory flows).
- **WARNING:** VL fallback, OpenAlex failures, dedup check failures.
- **ERROR:** `log.exception` on ingest failure/timeout.

**VL PDF path:** heavy work runs inside **`chain_span("ingest.parse_pdf.markdown", …)`**; **per-page progress** is pushed to **DB/SSE**. **Rate-limited INFO** heartbeats (`utils/ingest_vl_log_heartbeat.py`, env `SCIENCE_GRAPHRAG_INGEST_VL_LOG_HEARTBEAT_SECONDS`) emit pages done/total to stderr. **`httpx`** noise is reduced via **`SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL`** (default WARNING).

### 2.6 Phoenix / OpenTelemetry vs logs

**Files:** `science_graphrag/observability/init.py`, `docs/architecture/observability-phoenix.md`

- `phoenix.otel.register()` prints a **multi-line banner** to stdout on tracer init (seen in API and worker containers); exact text/volume depends on the **Phoenix library version**—mitigations in phase 2.4 are best-effort.
- **Spans** carry the **contract** for ingest (`ingest_document`, `ingest.<stage>`, attributes `metadata.job_id`, etc.).
- **`PHOENIX_TRACE_SCOPE`** gates volume; this is **orthogonal** to `SCIENCE_GRAPHRAG_LOG_LEVEL` — teams can have **verbose traces + quiet logs** or the opposite, often unintentionally.

### 2.7 Job-scoped text log (`ingest_jobs.logs`)

**Not stdlib logging**, but part of operator UX: `registry` appends truncated lines (`_append_log` in `api/ingest/worker.py`). The **string per job** is bounded (~48k chars); **many jobs** still mean growing table storage unless retention/archival is handled elsewhere. **No** unified correlation with stdout unless the same `job_id` appears in both.

---

## 3. Pain points (evidence-based)

| # | Symptom | Cause |
|---|---------|--------|
| P1 | Long **parse_pdf** / VL: Docker shows little except **`httpx` POST …/completions** | Domain progress in DB/SSE/Phoenix; pipeline rarely logs INFO inside tight loops. |
| P2 | **Dramatiq** startup floods logs | Many worker processes × “ready for action”. |
| P3 | **Phoenix** registration banner repeats (API reload, worker fork) | `register()` side effects + dev `--reload`. |
| P4 | **Two logger styles** (naming only) | Aliases vs `__name__` still differ; **levels/format** are aligned once `configure_logging()` runs (API lifespan, worker, CLI). |
| P5 | **Ingest poll 200** hidden from access log | By design; debugging “did UI poll?” needs temporary filter removal or DEBUG. |
| P6 | **Correlation** in stderr format | Mitigated: formatter includes `job_id=` / `workspace_id=` when context or `extra` is set. |
| P7 | Third-party **INFO** (httpx, etc.) | Mitigated: `SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL` / `SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL` in `configure_logging()`. |

---

## 4. Goals and non-goals

**Goals**

- G1 (**target after phases 1–2, not today**): An on-call engineer can answer **“what is job X doing right now?”** from **logs alone** within one grep, without opening Phoenix (Phoenix remains source of truth for span detail).
- G2: **Predictable** log volume in dev Docker (`docker compose logs`) — no multi-hundred-line startup surprises unless `DEBUG`.
- G3: **Single** documented way to set levels for app vs libraries vs access log.
- G4: Logs remain **safe** (no raw corpus text, no secrets); align with `security-sensitive` rules.

**Non-goals (for this plan)**

- Replacing Phoenix with logs.
- Full ELK/Loki deployment (only **enable** JSON / key=value for future shipping).

---

## 5. Improvement plan (phased)

**Status snapshot:** Phase **0–1** and most of **2** are implemented in-tree (runbook, `configure_logging` in API lifespan + worker, correlation filter + `ingest_log_context`, HTTP/Dramatiq log levels, VL heartbeats, Dramatiq dev compose + log level, `PHOENIX_OTEL_VERBOSE`). Phase **3** is **implemented** in-tree: JSON stderr (`SCIENCE_GRAPHRAG_LOG_FORMAT`, optional `trace_id` when an OTel span is active), Prometheus ingest counters + job-level and **per-stage** duration histograms ([`science_graphrag/observability/ingest_metrics.py`](../../science_graphrag/observability/ingest_metrics.py)), optional `SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST`; OTLP logs **deferred** per [ADR 026](../adr/026-otlp-logs-defer.md).

### Phase 0 — Documentation and knobs (same week, low risk)

| ID | Action | Acceptance |
|----|--------|------------|
| 0.1 | Add **`docs/runbooks/logging-and-troubleshooting.md`** (or extend existing runbook): list env vars (`SCIENCE_GRAPHRAG_LOG_LEVEL`, `PHOENIX_TRACE_SCOPE`, `PHOENIX_OPENAI_AUTO_INSTRUMENTATION`, `UVICORN_LOG_LEVEL` if used), where to look for ingest (**DB tables**, **SSE**, **Phoenix**), and how to temporarily **disable** ingest poll suppression. | New doc linked from `docs/architecture/observability-phoenix.md` “See also”. |
| 0.2 | Document **`ingest_jobs.logs`** field semantics and truncation in the same runbook. | Runbook section exists. |

### Phase 1 — Correlation and third-party tuning (small code, high value)

| ID | Action | Acceptance |
|----|--------|------------|
| 1.1 | **Centralize** `configure_logging()` in **API lifespan** and **worker module import path** (before Dramatiq workers fork if feasible), so every process has the same baseline. | Removing ad-hoc `configure_logging()` from scattered pipeline entrypoints does not break logging (or keep one redundant call as no-op). |
| 1.2 | Extend formatter or use **`logging.Filter`** to inject **`job_id`** when `contextvars` / `ContextVar` is set (ingest worker sets it at start of `_execute_single_ingest`; API sets for request-scoped middleware where applicable). | Sample log line contains `job_id=` for ingest worker lines during a job. |
| 1.3 | Add **env-driven** level map for noisy libraries, e.g. `SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL=WARNING` applied to `httpx`, `httpcore`, `urllib3` (documented defaults). | With default env, `docker compose logs worker` during VL shows **no** per-request httpx INFO unless user lowers threshold. |
| 1.4 | Optional: **`structlog`** not required — use stdlib `LoggerAdapter` or `extra=` convention: `{"job_id", "workspace_id", "stage"}`. | At least ingest worker path uses consistent `extra`. |

### Phase 2 — Ingest and worker “heartbeat” logging (moderate code)

| ID | Action | Acceptance |
|----|--------|------------|
| 2.1 | **Rate-limited INFO** (e.g. once per 60s or per N VL batches) in `vl_pdf` / pipeline: `job_id`, `stage`, `pages_done/total` or batch index. Uses `logging` `filter` or manual throttle. | Long VL run produces **≥1** INFO line per minute in steady state; no per-page spam at INFO. |
| 2.2 | **Actor** `ingest_document_actor`: INFO at **claim success** and **terminal** (completed/failed) with `job_id`, `kind`, duration if cheap. | `docker compose logs worker` shows clear job boundaries. |
| 2.3 | **Dramatiq:** reduce process count in **dev** compose override **or** lower Dramatiq’s own logger to WARNING in dev profile (document tradeoff: slower parallel ingest). | Default dev `docker compose logs worker --tail 30` after boot fits ~30 lines without 20× duplicate. |
| 2.4 | **Phoenix banner:** if upstream allows, set quiet mode **or** log banner at DEBUG only (wrapper after `register()`). If not feasible, document **one-time** stderr redirect for tests only. | Repeat API reload produces **≤N** lines of Phoenix boilerplate (target: 0–3). |

### Phase 3 — Production-oriented (optional, larger)

| ID | Action | Acceptance |
|----|--------|------------|
| 3.1 | **`SCIENCE_GRAPHRAG_LOG_FORMAT=json`** (or similar): JSON lines to stderr with stable keys (`ts`, `level`, `logger`, `msg`, `job_id`, …). | **Done:** [`project_logging.py`](../../science_graphrag/utils/project_logging.py), tests [`test_project_logging_json.py`](../../tests/utils/test_project_logging_json.py), runbook. |
| 3.2 | **OpenTelemetry Logs** bridge (OTLP log exporter) — only if product standardizes on single backend; coordinate with Phoenix vendor capabilities. | **Done (defer):** [ADR 026](../adr/026-otlp-logs-defer.md) — use JSON stderr + optional `/metrics` first; OTLP logs pilot later behind a flag. |
| 3.3 | **Metrics** counters for ingest (Prometheus): `ingest_jobs_started_total`, terminal counter, job + **per-stage** duration histograms — complements logs. | **Done:** `ingest_jobs_started_total`, `ingest_jobs_terminal_total{kind,status}`, `ingest_job_duration_seconds`, `ingest_stage_duration_seconds{stage,status}` in [`ingest_metrics.py`](../../science_graphrag/observability/ingest_metrics.py); stage hooks in [`stage_context.py`](../../science_graphrag/ingestion/stage_context.py); worker hooks; `GET /metrics` when `SCIENCE_GRAPHRAG_METRICS_ENABLED=true`. |

### Phase 4 — Consistency and hygiene (ongoing)

| ID | Action | Acceptance |
|----|--------|------------|
| 4.1 | Lint or guideline: **new** modules prefer `get_logger` **or** a single `logging.getLogger(__name__)` policy — pick one and document in `.cursor/rules/backend-quality.mdc` or architecture doc. | **Done:** *Logging conventions* in [`.cursor/rules/backend-quality.mdc`](../../.cursor/rules/backend-quality.mdc); cross-link in [`observability-phoenix.md`](../architecture/observability-phoenix.md). |
| 4.2 | Audit **`print()`** and stray **DEBUG** left in hot paths (ingestion, agent). | **Done:** corpus CLI summaries in [`_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py) use `logger.info`; allowlisted `print` in [`cli_preflight.py`](../../science_graphrag/storage/cli_preflight.py) (early CLI exit). |
| 4.3 | Align **`idea_assist`** / **`task_store`** log variable names (`log` vs `logger`) for readability only. | **Done:** `idea_assist` uses `logger`; `task_store` already used `logger`. |

---

## 6. Testing and verification

| Check | Method |
|-------|--------|
| No secret leakage | Grep logs fixtures + manual ingest with fake key rotation; runbook checklist. |
| Volume | Script: run single VL PDF ingest, count stderr lines at INFO default — baseline + regression budget. |
| Correlation | Assert in integration test that worker log record contains `job_id` when ContextVar set (caplog). |

---

## 7. Relation to other tracks

- **Phoenix / tracing:** [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md) — logs must **not** duplicate span payloads; they should **point** to trace id when available (`phoenix_trace_id` on job).
- **Long-running ingest:** `.cursor/rules/long-running-ops.mdc` — heartbeats in logs align with “progress at least every N minutes” operational goal.
- **Security:** `.cursor/rules/security-sensitive.mdc` — heartbeat messages must be **counts and ids**, not document text.

---

## 8. Open questions

1. **Implemented:** successful ingest job **GET** polling at INFO is logged when the request line contains `debug=1` / `debug=true` (see `_SuppressIngestPolling` in `api/main.py`).
2. **Resolved (2026-04-28):** dev compose sets `SCIENCE_GRAPHRAG_DRAMATIQ_PROCESSES=1` and `SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL` defaults to `WARNING` in `configure_logging()`; raise processes or threads via env/CLI when batch throughput matters.
3. **`ingest_jobs.logs`** remains the **user-visible** job tail in the workspace UI; **Docker/stderr** is for operators and aggregation — see i18n `partWorkspacePage` job log hint strings (EN/RU).

---

## 9. Summary table (priority)

| Priority | Phase | Theme |
|----------|-------|--------|
| P0 | 0 | Runbook + env documentation |
| P1 | 1 | Central configure + library levels + correlation |
| P2 | 2 | Ingest heartbeats + worker boundaries + dev noise |
| P3 | 3 | JSON / OTLP logs / metrics (product decision) |
| P4 | 4 | Style consistency |

---

*End of document.*
