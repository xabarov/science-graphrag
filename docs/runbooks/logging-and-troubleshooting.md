# Logging and troubleshooting (backend)

Text logs (`stderr`), Uvicorn access logs, ingest job tail (`ingest_jobs.logs`), SSE, and Phoenix traces are **different surfaces**. Use this runbook to tune verbosity and find signals without leaking corpus text or secrets. See also [observability-phoenix.md](../architecture/observability-phoenix.md) for span naming and trace scope.

## Environment variables

| Variable | Effect |
|----------|--------|
| `SCIENCE_GRAPHRAG_LOG_LEVEL` | Level for logger `science_graphrag` (default `INFO`). Applied when `configure_logging()` runs (API lifespan, worker import, CLI callback, or first `get_logger` under `science_graphrag.*`). |
| `SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST` | Optional: override level **only** for subtree `science_graphrag.ingestion` (e.g. `DEBUG` for pipeline without raising noise from API). Unset = inherit `SCIENCE_GRAPHRAG_LOG_LEVEL`. |
| `SCIENCE_GRAPHRAG_LOG_FORMAT` | `text` (default) or `json` — stderr lines from the `science_graphrag` handler as structured JSON (`ts`, `level`, `logger`, `msg`, `job_id`, `workspace_id`, optional `stage`, optional `trace_id` when an OpenTelemetry span with valid trace id is active). |
| `SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL` | Level for `httpx`, `httpcore`, `urllib3` (default `WARNING`). Reduces per-request HTTP lines during VL PDF and other API calls. |
| `SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL` | Level for logger `dramatiq` (default `WARNING`). Quiets Dramatiq worker boot lines unless set to `INFO` or `DEBUG`. |
| `SCIENCE_GRAPHRAG_DRAMATIQ_PROCESSES` | When `python -m science_graphrag.worker` is started **without** extra CLI args, worker passes `--processes` to Dramatiq from this value. Empty = Dramatiq default (many processes). Compose dev sets `1` to limit boot noise. |
| `SCIENCE_GRAPHRAG_DRAMATIQ_THREADS` | Same pattern for `--threads` when no CLI overrides. Empty = Dramatiq default. |
| `SCIENCE_GRAPHRAG_INGEST_VL_LOG_HEARTBEAT_SECONDS` | Minimum interval between INFO heartbeat lines during VL PDF parse (default `60`). Counts only; no paths or document text. |
| `SCIENCE_GRAPHRAG_INGEST_PIPELINE_LOG_HEARTBEAT_SECONDS` | Minimum interval between INFO “progress” lines during a long non-VL stage (`flush_progress`). Stage boundaries log once per stage name when pipeline heartbeat context is active. |
| `SCIENCE_GRAPHRAG_METRICS_ENABLED` | When `true`, API exposes `GET /metrics` (Prometheus text). Default `false`. |
| `PHOENIX_TRACE_SCOPE` | Volume of exported spans; orthogonal to log level. See observability doc. |
| `PHOENIX_OPENAI_AUTO_INSTRUMENTATION` | `0` / `off` to disable OpenAI auto-instrumentation if it duplicates hand-authored spans. |
| `PHOENIX_OTEL_VERBOSE` | If set to `1` / `true` / `yes` / `on`, Phoenix `register(verbose=…)` prints console diagnostics. If **unset**, `verbose` follows `ENV`: **false** in `dev`, `local`, `test`; **true** in other environments. |
| `UVICORN_LOG_LEVEL` | Standard Uvicorn env when launching `uvicorn` (not set by app code). |

Smoke check:

```bash
.venv/bin/science-graphrag config-check
```

## Where to look during ingest

1. **Postgres** — `ingest_jobs` row: `status`, `message`, `progress_*`, `logs` (text tail), `phoenix_trace_id` when set.
2. **SSE / UI** — job stream events (`stage_progress`, `stage_started`, …) from the API event bus.
3. **Phoenix** — span detail for `ingest_document`, `ingest.<stage>`, `llm.vl_pdf`, etc.
4. **Docker / process logs** — `science_graphrag` lines include `job_id=` and `workspace_id=` when ingest worker or actor runs with `ingest_log_context` (see `science_graphrag/utils/log_context.py`).

## Ingest job text log (`ingest_jobs.logs`)

- Appended by the ingest worker ([`api/ingest/worker.py`](../../science_graphrag/api/ingest/worker.py)); not the stdlib logging tree.
- Each job row stores a **single string** capped at **48_000 characters** (oldest text drops as new lines append).
- **Retention** is per job row: many jobs mean many rows; archival or pruning is a separate ops concern.
- Do not rely on this field for large dumps; it is for operator/user-visible tail only.

## Uvicorn access log: ingest job polling

Successful **GET** requests to `/v1/ingest/jobs/` that return **200** are filtered out at **INFO** to reduce noise from UI polling (`_SuppressIngestPolling` in [`science_graphrag/api/main.py`](../../science_graphrag/api/main.py)). If the access log line contains **`debug=1`** or **`debug=true`** (query string on the request line), the line is **not** suppressed so you can confirm polling in `docker compose logs api`.

To debug polling otherwise:

- Run API with access log at **DEBUG** if your deployment supports it, or
- Temporarily remove or narrow the filter in `main.py` (revert before commit), or
- Use Postgres / SSE / Phoenix instead of access logs for poll debugging.

## Phoenix registration on stderr

Tracer init may print Phoenix / OpenTelemetry diagnostics to stderr. See [`docs/architecture/observability-phoenix.md`](../architecture/observability-phoenix.md) section **Python stderr during `phoenix.otel.register()`** and env `PHOENIX_OTEL_VERBOSE`.

## Dramatiq worker in development

Default Dramatiq **process** count is high; combined with per-process boot logs this floods `docker compose logs worker`.

- **docker-compose.dev.yml** sets `SCIENCE_GRAPHRAG_DRAMATIQ_PROCESSES=1` for a quieter default (fewer parallel ingest jobs per host).
- Override with `SCIENCE_GRAPHRAG_DRAMATIQ_PROCESSES` / `SCIENCE_GRAPHRAG_DRAMATIQ_THREADS` or pass arguments after the module: `python -m science_graphrag.worker --processes 4 --threads 8`.

## Further reading

- Analysis and phased plan: [logging-system-deep-dive-and-improvement-plan-2026-04-28.md](../analysis/logging-system-deep-dive-and-improvement-plan-2026-04-28.md)
- Security: `.cursor/rules/security-sensitive.mdc` — never log raw corpus, tokens, or secrets.
