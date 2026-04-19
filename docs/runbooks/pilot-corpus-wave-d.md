# Pilot corpus — Wave D (CV / object detection)

Operational notes for ingesting the **10–50 PDF** pilot corpus in the computer vision / object-detection lane. Complements [pilot-checklist.md](pilot-checklist.md).

## Prerequisites

1. Stack up: `docker compose up -d` (see [deploy.md](deploy.md)) — Postgres, Neo4j, Qdrant.
2. `.env` configured for stores and LLM (below).

## Environment variables (LLM + semantic extraction)

Set in `.env` or the shell (see [science_graphrag/config.py](../../science_graphrag/config.py) for full list):

- **Main / shared LLM:** `MAIN_LLM_API_KEY` and related `MAIN_LLM_*` (model, base URL) as used by the CLI.
- **Extraction LLM (Layer 1 + semantic):** `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY`, `SCIENCE_GRAPHRAG_EXTRACTION_LLM_BASE_URL`, `SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL`, or rely on merge rules that fall back to `MAIN_LLM_*` / `API_KEY` per [deploy.md](deploy.md).
- **Semantic stage toggle:** `SCIENCE_GRAPHRAG_SEMANTIC_EXTRACTION_ENABLED` (default on when an LLM is configured).
- **Stores:** `SCIENCE_GRAPHRAG_DATABASE_URL`, Neo4j and Qdrant URLs/collection as in [deploy.md](deploy.md).

Without LLM keys, backbone ingest may still run, but **Method/Dataset** semantic edges will not populate; align expectations with the pilot KPI table.

## Corpus size target (Wave D3)

Aim for **N≥20–50** ingested works in the pilot corpus before declaring pilot **GO**, so list/search, graph, and Ask behaviors are exercised beyond a demo-sized set. The 2026-04-06 KPI snapshot used **38** works — acceptable for **CONDITIONAL-GO**; grow the corpus and re-run spot-check + latency when feasible.

## Default host corpus (CV / object detection, 31 PDF)

For the Wave D domain in [pilot-checklist.md](pilot-checklist.md), a convenient **host path** (outside this repo) is:

`/home/roman/Documents/ML/CV/object-detection`

It matches benchmark `SOURCE.txt` references under `tests/fixtures/benchmarks/layer1/*_realpdf/`. Full pilot ingest:

```bash
# optional: export PILOT_CORPUS_DIR=/other/path/to/pdfs
./scripts/pilot_ingest_cv_corpus.sh
```

## Ingest corpus

From the repo root (active `.venv` recommended):

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/pilot/pdfs
```

- Recursively picks up `.pdf`, `.md`, `.txt`.
- After the run, review **dedup** output from the corpus CLI and Neo4j audit messages.

## Dedup and merge

- Post-ingest dedup guidance and optional merge: **same** [deploy.md](deploy.md) *Ingest* section (`merge-work` when manual resolution is required).
- Do not start KPI counting until duplicate `Work` clusters are understood or merged.

## Mandatory happy-path (API)

After at least one successful ingest, validate the **Mandatory API happy-path** in [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) (Wave C): ingest → `GET /v1/works` → `GET /v1/works/{id}` → `POST /v1/query` → `GET /v1/works/{id}/chunks`. Full automation requires live services: `pytest -m integration` with compose up.

## Exit artifact

Record dates, corpus path (redacted if needed), and decision in [docs/pilot/wave-d-exit-record.md](../pilot/wave-d-exit-record.md) and the pilot checklist.

**KPI latency (optional):** with API on `8787`, run `BASE=http://127.0.0.1:8787 N=40 ./scripts/pilot_measure_latency.sh` and paste JSON summary into the exit record.

**Citation spot-check (N=5):** `BASE=http://127.0.0.1:8787 ./scripts/pilot_spot_check.sh` — fixed `POST /v1/query` probes for `work_id` + provenance fields; see [wave-d-exit-record.md](../pilot/wave-d-exit-record.md).

