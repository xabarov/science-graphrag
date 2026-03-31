# Runbook: deploy

## Stack

- **Postgres**: document metadata and ingestion runs (`SCIENCE_GRAPHRAG_DATABASE_URL`).
- **Neo4j**: scholarly backbone + ontology v1 `Method` / `Dataset` edges.
- **Qdrant**: section-aware chunks and embeddings for retrieval.
- **API** (optional): `science-graphrag-api` serves FastAPI on port 8787 (`/health`, `/v1/query`, static UI at `/`).

## Configuration

- Copy `.env.example` to `.env` if present, or set `SCIENCE_GRAPHRAG_*` variables (see [science_graphrag/config.py](../../science_graphrag/config.py)).
- Extraction LLM keys: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` or reuse `MAIN_LLM_*` / `API_KEY` per settings merge rules.
- **Semantic stage**: `SCIENCE_GRAPHRAG_SEMANTIC_EXTRACTION_ENABLED` (default on when LLM available).

## Compose

- Bring up dependencies with project `docker-compose.yml` (Neo4j bolt port, Postgres, Qdrant as configured locally). Use **`docker compose` without `sudo`** (Linux: user in `docker` group; or Docker Desktop).
- Install package: `pip install -e ".[dev]"(embed optional for sentence-transformers)`.
- Initialize SQL schema via first ingest or app that calls `init_db`.
- Rebuild after backend changes when validating e2e: e.g. `docker compose up -d --build` (see roadmap **Execution policy**).

## Benchmarks and decision gate

- Full LLM benchmark runs and the metrics aggregator may be executed as part of roadmap validation **without extra confirmation**; ensure `.env` has LLM keys for tier `nightly_*` (see [eval/README.md](../../eval/README.md)).
- After runs: `.venv/bin/python scripts/aggregate_benchmark_metrics.py` — see [benchmark-decision-gate.md](benchmark-decision-gate.md).

## Ingest

- Single file: `science-graphrag ingest path/to/paper.pdf`
- Corpus: `science-graphrag ingest-corpus /data/corpus`
- After bulk ingest, review Neo4j dedup audit printed by corpus CLI; optional manual merge: `science-graphrag merge-work <keep_work_id> <drop_work_id>` (drops duplicate only if it has no authorship rows).

## API process

Production-style: run behind reverse proxy TLS termination; bind API to localhost or private network. Example:

```bash
SCIENCE_GRAPHRAG_QDRANT_URL=http://127.0.0.1:16333 \
science-graphrag-api
```

## CI vs prod

- Merge CI: unit tests + layer-2 merge_safe benchmark without LLM.
- Nightly: integration pytest + layer-1/graph suites + layer-2 suite (see workflows).
