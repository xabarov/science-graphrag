# Phase 0 — OpenRouter `baai/bge-m3` Qdrant cutover (ADR-021)

Operational sequence to move dense-vector stores from **384-dim hash** (or legacy ST) to **1024-dim OpenRouter `baai/bge-m3`**, then repopulate vectors. See [`docs/adr/021-openrouter-bge-m3-embeddings.md`](../adr/021-openrouter-bge-m3-embeddings.md) for rationale and risks.

## Preconditions

1. **Docker stack healthy** — Postgres, Neo4j, Qdrant (and Redis if ingest uses the worker path):

   ```bash
   docker compose ps --format 'table {{.Service}}\t{{.Status}}'
   ```

2. **API keys in the process environment** — embeddings use the same OpenRouter-compatible credentials as extraction (`MAIN_LLM_API_KEY` / `SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY` + base URL). Smoke:

   ```bash
   .venv/bin/science-graphrag config-check --no-strict
   ```

   Expect `embeddings channel … openrouter (model=baai/bge-m3, dim=1024)` when cutover env is set.

3. **`.env` (or exports)** — at minimum:

   ```bash
   SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL=baai/bge-m3
   SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_DIM=1024
   # Optional cache location (defaults under ./data/embeddings_cache)
   # SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_CACHE_ROOT=./data/embeddings_cache
   ```

   If you mistakenly set `SCIENCE_GRAPHRAG_EMBEDDING_MODEL=org/model` (hub id), `Settings.merge_osint_gr_compatible_env` promotes that into `openrouter_embedding_model` so `resolve_embedder` still picks OpenRouter (see `tests/test_embedding_model_promotion.py`).

## Step 1 — Dry-run (no deletes)

Lists target collection names, current presence in Qdrant, and resolved `vector_dim`:

```bash
.venv/bin/science-graphrag qdrant-recreate-embedding-collections --dry-run
```

## Step 2 — Drop and recreate empty collections

**Destructive:** removes all points in `chunks`, `work_embeddings`, `claims`, `author_embeddings`, and entity-dedup collections. Neo4j `:Work` nodes are **not** deleted.

```bash
.venv/bin/science-graphrag qdrant-recreate-embedding-collections
```

Confirm the CLI prints `vector_dim=1024` (or your configured OpenRouter dim).

## Step 3 — Re-ingest corpus (repopulate Qdrant + pipelines)

Chunks and work-level vectors must be rebuilt. Use the same blob root and DB URLs as the API if you serve PDFs from Docker.

```bash
# Example: pilot CV corpus (override path as needed)
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress-phase0-bge-m3.jsonl
```

Resume after interruption:

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --resume \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress-phase0-bge-m3.jsonl
```

Shell helper: `scripts/pilot_ingest_cv_corpus.sh` (see comments inside for `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV` and Postgres URL alignment). Full checklist for timeouts and blobs: [`ingest-corpus.md`](ingest-corpus.md).

Optional: **work title embeddings** in Neo4j (if you use that index) after chunks exist:

```bash
.venv/bin/python scripts/backfill_work_embeddings.py
```

(Only if your deployment relies on that script; many paths embed during ingest.)

## Embeddings preflight + per-document Qdrant resume

If OpenRouter returns **no successful provider** for embeddings (HTTP 200 with `data: null` / 404 in payload), full ingest still **commits Postgres + Neo4j through claims** before the embed stage; use:

```bash
# Fail fast before a long corpus run (optional)
.venv/bin/science-graphrag config-check --embeddings-preflight
.venv/bin/science-graphrag ingest-corpus /path/to/corpus --embeddings-preflight …
```

To **re-run only Qdrant** for one `documents.id` (requires `normalized.md` under `artifact_root` and `work_id` on the row):

```bash
.venv/bin/science-graphrag ingest-resume-embed <document_uuid>
```

Checkpoint JSON on `documents.ingest_checkpoint_json` records `embed` stage status (`failed_retryable` vs `completed`). Claims vectors in Qdrant are **not** rebuilt by `ingest-resume-embed` (use full re-ingest for claims+Neo4j repair).

## Step 4 — Benchmarks and trust snapshot

After the corpus is back in Qdrant:

```bash
.venv/bin/python scripts/aggregate_benchmark_metrics.py \
  --write-trust-baseline eval/results/benchmark-trust-baseline.json
.venv/bin/pytest tests/benchmarks/test_trust_baseline_regression.py -q
```

Re-run retrieval / hybrid / workspace live suites as needed for BT2–BT5 (see master roadmap §10).

## Rollback

There is **no** in-place downgrade from 1024 to 384: you would unset OpenRouter embedding env, run `qdrant-recreate-embedding-collections` again (collections would be recreated at hash/ST dim), and **re-ingest** again.
