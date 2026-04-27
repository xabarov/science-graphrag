# ingest-corpus runbook

`science-graphrag ingest-corpus` now supports per-file timeout and resume checkpointing.

After a **Qdrant embedding cutover** (drop/recreate collections at a new vector size), you must re-ingest — see [`phase0-bge-m3-qdrant-cutover.md`](phase0-bge-m3-qdrant-cutover.md).

## Recommended command

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress-wave5.jsonl
```

Optional: use a merged/writable blob tree (same variable the API should use for PDFs):

```bash
export SCIENCE_GRAPHRAG_BLOB_ROOT="$PWD/data/blobs_merged"
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --per-file-timeout-s 900 \
  --progress-file eval/results/ingest-progress-wave5.jsonl
```

Shell-exported `SCIENCE_GRAPHRAG_BLOB_ROOT` is respected in all modes (with or without `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1`); align `.env` or Compose env for **api/worker** so downloads match ingest.

When re-running the **same** pilot tree after a partial ingest, add `--skip-existing-sha` so files already in `documents` are not re-extracted.

**Claims caveat:** `--skip-existing-sha` skips the whole pipeline for matching PDFs, so **claims are not refreshed** for those documents. If chunks already exist in Qdrant but Neo4j has no (or stale) claims, use the claims-only helper instead of a full re-ingest:

```bash
.venv/bin/python scripts/backfill_workspace_claims.py \
  --workspace-id "<WORKSPACE_UUID>" \
  --progress-file eval/results/claims-backfill.jsonl
```

Add `--resume` to continue after interruption. See the script docstring for `--force-all` and dry-run.

## Pre-flight: PDFs vs catalog (P0 slugs)

Heuristic mapping of filenames to `corpus_work_id` (see `tests/fixtures/corpus/CATALOG.md`):

```bash
.venv/bin/python scripts/verify_pilot_corpus_against_catalog.py "$PILOT_CORPUS_DIR"
```

## Post-flight: distinct works in Qdrant (Wave 5 acceptance)

Roadmap target: **≥16** distinct `work_id` values in the configured `chunks` collection.

```bash
.venv/bin/python scripts/report_qdrant_work_coverage.py --min-works 16
```

Omit `--min-works` for a read-only report (always exits 0).

**Neo4j (optional):** total `:Work` nodes (includes works without chunks if any):

```cypher
MATCH (w:Work)
RETURN count(w) AS work_count;
```

## Flags

- `--per-file-timeout-s` — hard wall timeout per file in seconds; `0` disables timeout.
- `--resume` — skip files that already have `status=ok` in progress JSONL.
- `--progress-file` — path to JSONL checkpoint file.

## Progress JSONL format

Each processed file appends one JSON line:

```json
{"path":"/abs/file.pdf","status":"ok|fail|timeout|skip","document_id":"...","work_id":"...","started_at":"...","finished_at":"...","error":null}
```

Use the same `--progress-file` path with `--resume` after interruption:

```bash
.venv/bin/science-graphrag ingest-corpus /path/to/corpus \
  --continue-on-error \
  --resume \
  --progress-file eval/results/ingest-progress-wave5.jsonl
```

## Troubleshooting

### Postgres `password authentication failed` when `.env` disagrees with Docker

`Settings` loads `.env` from the repo root. If `SCIENCE_GRAPHRAG_DATABASE_URL` there uses a password that **does not match** the Postgres volume created by `docker-compose.dev.yml` (default user/password: `science` / `change-me` on host port `15432`), batch ingest fails before the first file.

**Fix (pick one):**

1. Align `.env` with compose defaults for local dev, **or**
2. Export overrides **after** sourcing `.env`, **or**
3. Run with `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1` and set storage URLs explicitly in the environment (same pattern as `docker-compose.dev.yml` `api` service). Example:

```bash
export SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1
export SCIENCE_GRAPHRAG_DATABASE_URL='postgresql+psycopg://science:change-me@localhost:15432/science_graphrag'
export SCIENCE_GRAPHRAG_REDIS_URL='redis://localhost:16379/0'
export SCIENCE_GRAPHRAG_NEO4J_URI='bolt://localhost:17687'
export SCIENCE_GRAPHRAG_QDRANT_URL='http://localhost:16333'
# Keep LLM credentials in the environment for VL + extraction (canonical
# SCIENCE_GRAPHRAG_* keys or legacy MAIN_LLM_API_KEY / OPENROUTER_API_KEY / API_KEY).
```

### `PermissionError` on `data/blobs/raw/...`

If some shard dirs are **root-owned** (typical after a root-run Docker bind-mount), `chmod` as a normal user will not help — use `sudo chown -R "$USER:$USER" data/blobs/raw` once, **or** (no sudo) copy readable blobs into a writable tree and point **both** shell and `SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1` at it:

```bash
mkdir -p data/blobs_merged/raw
rsync -a data/blobs/raw/ data/blobs_merged/raw/
export SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV=1
export SCIENCE_GRAPHRAG_BLOB_ROOT="$PWD/data/blobs_merged"
# …same Postgres/Neo4j/Qdrant overrides as in «Postgres» subsection…
```

Then run `ingest-corpus` with `--resume`. For day-to-day dev, either keep `SCIENCE_GRAPHRAG_BLOB_ROOT` in `.env` aligned with that tree or merge back after `chown`.

**Docker API (`docker-compose.dev.yml`):** set `SCIENCE_GRAPHRAG_HOST_BLOB_MOUNT=./data/blobs_merged` in `.env` so the `api` / `worker` bind-mount matches the merged tree (same variable as host path; defaults to `./data/blobs`). Restart `api` after changing it.

## Live log streaming

If you tee logs, force line buffering so progress is visible in real time:

```bash
stdbuf -oL .venv/bin/science-graphrag ingest-corpus /path/to/corpus | tee ingest.log
```

or:

```bash
unbuffer .venv/bin/science-graphrag ingest-corpus /path/to/corpus | tee ingest.log
```
