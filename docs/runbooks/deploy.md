# Runbook: deploy

## Policy: Docker and Compose (early)

- **Goal:** одинаково воспроизводимое окружение для локальной разработки, интеграционных тестов и тяжёлых прогонов (бенчмарки, e2e), без ручной установки СУБД и векторного стора на каждой машине.
- **Requirement:** новые **stateful** зависимости (БД, очереди, поиск, векторы) и **долеживаемые** сервисы приложения по возможности сразу добавлять в **`docker-compose.yml`** и при необходимости сопровождать **Dockerfile**, а не откладывать контейнеризацию до «продакшена».
- **Default workflow:** `docker compose up -d` из корня репозитория; порты и переменные окружения согласовать с [benchmark-stabilization-baseline.md](benchmark-stabilization-baseline.md) и `science_graphrag/config.py`.
- **После правок backend/API:** для согласованного e2e — `docker compose up -d --build` (см. roadmap, раздел **Execution policy**).

## Stack

- **Postgres**: document metadata and ingestion runs (`SCIENCE_GRAPHRAG_DATABASE_URL`).
- **Neo4j**: scholarly backbone + ontology v1 `Method` / `Dataset` edges.
- **Qdrant**: section-aware chunks and embeddings for retrieval.
- **API** (`api` service): FastAPI on port **8787** inside the compose network (`/health`, `/v1/*`). Published on the host as **18787** for optional direct access (bypasses nginx).
- **Web** (`web` service): nginx on host **8787** — serves the Vite UI under `/ui` and proxies `/v1`, `/health`, etc. to `api`. Rebuild only the UI after frontend changes: `docker compose build web` (does not reinstall Python deps). Rebuild only the backend: `docker compose build api`.

## Configuration

- Copy `.env.example` to `.env` if present, or set `SCIENCE_GRAPHRAG_*` variables (see [science_graphrag/config.py](../../science_graphrag/config.py)).
- Extraction LLM keys: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` (see `science_graphrag/config.py` and `.env.example`).
- **Semantic stage**: `SCIENCE_GRAPHRAG_SEMANTIC_EXTRACTION_ENABLED` (default on when LLM available).

## Compose

- Bring up dependencies with project `docker-compose.yml` (Neo4j bolt port, Postgres, Qdrant as configured locally). Use **`docker compose` without `sudo`** (Linux: user in `docker` group; or Docker Desktop).
- Install package: `pip install -e ".[dev]"` (optional embeddings: `pip install -e ".[dev,embed]"`).
- Initialize SQL schema via first ingest or app that calls `init_db`.
- Rebuild after backend changes when validating e2e: e.g. `docker compose up -d --build api web` or `docker compose build api && docker compose up -d` (see roadmap **Execution policy**). After **only** `ui/` changes: `docker compose build web && docker compose up -d web`.

## Benchmarks and decision gate

- Full LLM benchmark runs and the metrics aggregator may be executed as part of roadmap validation **without extra confirmation**; ensure `.env` has LLM keys for tier `nightly_*` (see [eval/README.md](../../eval/README.md)).
- After runs: `.venv/bin/python scripts/aggregate_benchmark_metrics.py` — see [benchmark-decision-gate.md](benchmark-decision-gate.md).

## Ingest

- Single file: `science-graphrag ingest path/to/paper.pdf`
  - **Default (with Postgres):** same file bytes (`sha256`) **reuse** one existing `document_id` (if several rows share the hash — e.g. after `--force-new-document` — the **newest** by `created_at` is used); old Qdrant points for that id are removed before re-upsert (no duplicate chunks for one document).
  - `--skip-existing-sha` — skip if hash already in `documents` (corpus re-runs).
  - `--force-new-document` — always new `document_id` (debug / avoid SQL dedup).
- Corpus: `science-graphrag ingest-corpus /data/corpus` (same flags: `--skip-existing-sha`, `--force-new-document`).
- After bulk ingest, review Neo4j dedup audit printed by corpus CLI; optional manual merge: `science-graphrag merge-work <keep_work_id> <drop_work_id>` (drops duplicate only if it has no authorship rows). **`merge-work` also rewrites Qdrant chunk payloads** from `drop_work_id` to `keep_work_id` when the duplicate node is removed, so Ask → Reader stays consistent.
- If citations still show a `work_id` that returns `work_not_found` (e.g. merge before this fix): `science-graphrag diagnose-qdrant-work-ids` then `science-graphrag repoint-qdrant-work-ids <keep_work_id> <stale_work_id>` for each orphan (same order as `merge-work`: keep first, drop second).

## Qdrant maintenance (CLI)

- `science-graphrag delete-qdrant-by-document-id <document_id>` — drop all points with that payload.
- `science-graphrag delete-qdrant-by-work-id <work_id>` — drop all chunks for a work (destructive).
- `science-graphrag qdrant-recreate-collection` — delete and recreate the configured collection (empty). **Dev only.**

## Purge one work (MVP)

- `science-graphrag purge-work <work_id>` — deletes Qdrant points for that `work_id`.
- `science-graphrag purge-work <work_id> --detach-neo4j` — also `DETACH DELETE` the `:Work` if it exists **and** no other `(:Work)-[:CITES]->(w)` (fails with exit 1 otherwise).

## Dev stack reset (avoid Qdrant ↔ Neo4j orphans)

`neo4j-wipe` alone leaves **Qdrant** pointing at deleted `work_id` values. Recommended sequence:

1. `science-graphrag neo4j-wipe`
2. `science-graphrag qdrant-recreate-collection`
3. Optionally truncate SQL tables if you need a clean ledger: `TRUNCATE ingestion_runs, documents RESTART IDENTITY CASCADE;` (Postgres; adjust schema if needed).
4. Re-ingest corpus.

Wrapper (review before run): [`scripts/stack_reset_dev.sh`](../../scripts/stack_reset_dev.sh).

## API process

Production-style: run behind reverse proxy TLS termination; bind API to localhost or private network. Example:

```bash
SCIENCE_GRAPHRAG_QDRANT_URL=http://127.0.0.1:16333 \
science-graphrag-api
```

## CI vs prod

- Merge CI: unit tests + layer-2 merge_safe benchmark without LLM.
- Nightly: integration pytest + layer-1/graph suites + layer-2 suite (see workflows).

## Pilot readiness (Phase 7)

Before a **research pilot** on shared infrastructure:

1. **Benchmark gate:** `GO` or **CONDITIONAL-GO** with documented blockers — [benchmark-decision-gate.md](benchmark-decision-gate.md) (Wave A must not be NO-GO).
2. **Operational:** stack from this runbook up; backups and API keys per project policy.
3. **Checklist:** [pilot-checklist.md](pilot-checklist.md) (KPI + mandatory API happy-path from [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md)).

## End-to-end validation

After ingest, validate the **Mandatory API happy-path** (same as Wave C in [roadmap-next-waves.md](roadmap-next-waves.md)): `GET /v1/works` → `GET /v1/works/{id}` → `POST /v1/query` → `GET /v1/works/{id}/chunks` (see contracts doc for full steps).

**Compose + API smoke (8787):** from repo root, `./scripts/smoke_compose_api.sh` — `docker compose up -d --build`, wait for `GET /health`, then `GET /v1/works?limit=1`.
