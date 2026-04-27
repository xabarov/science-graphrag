#!/usr/bin/env bash
# Wave D pilot: ingest the default CV object-detection corpus (31 PDFs).
# Prereq: docker compose up -d; .env with DB URLs and optional LLM keys.
# Override directory: PILOT_CORPUS_DIR=/path/to/pdfs ./scripts/pilot_ingest_cv_corpus.sh
# Dry run (count only): PILOT_DRY_RUN=1 ./scripts/pilot_ingest_cv_corpus.sh
# Re-run after partial ingest: INGEST_RESUME=1 INGEST_SKIP_EXISTING_SHA=1 ./scripts/pilot_ingest_cv_corpus.sh
# Writable merged blobs: PILOT_USE_BLOBS_MERGED=1 (default) uses data/blobs_merged if present.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# If operator rsync'd blobs into data/blobs_merged (root-owned raw tree), default ingest there.
# Opt out: PILOT_USE_BLOBS_MERGED=0 or set SCIENCE_GRAPHRAG_BLOB_ROOT explicitly.
if [[ -z "${SCIENCE_GRAPHRAG_BLOB_ROOT:-}" && "${PILOT_USE_BLOBS_MERGED:-1}" == "1" ]]; then
  if [[ -d "$ROOT/data/blobs_merged/raw" ]]; then
    export SCIENCE_GRAPHRAG_BLOB_ROOT="$ROOT/data/blobs_merged"
    echo "Using SCIENCE_GRAPHRAG_BLOB_ROOT=$SCIENCE_GRAPHRAG_BLOB_ROOT (set PILOT_USE_BLOBS_MERGED=0 to skip)."
  fi
fi

# Host CLI against docker-compose.dev.yml: `.env` often pins `science:science` for Postgres,
# while compose defaults to `science:change-me`. Prefer explicit URLs when SKIP_HOST_DOTENV=1.
# IMPORTANT: if SKIP_HOST_DOTENV=1, set SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY (and VL if used)
# in `.env` or export them in the shell so extraction + VL PDF stages do not hang with empty keys
# (see docs/runbooks/ingest-corpus.md).
export SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV="${SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV:-1}"
export SCIENCE_GRAPHRAG_DATABASE_URL="${SCIENCE_GRAPHRAG_DATABASE_URL:-postgresql+psycopg://science:change-me@localhost:15432/science_graphrag}"
export SCIENCE_GRAPHRAG_REDIS_URL="${SCIENCE_GRAPHRAG_REDIS_URL:-redis://localhost:16379/0}"

DEFAULT_CORPUS="${PILOT_CORPUS_DIR:-/home/roman/Documents/ML/CV/object-detection}"
if [[ ! -d "$DEFAULT_CORPUS" ]]; then
  echo "Corpus directory missing: $DEFAULT_CORPUS" >&2
  echo "Set PILOT_CORPUS_DIR to a folder with 10–50 PDFs." >&2
  exit 1
fi

if [[ ! -x .venv/bin/science-graphrag ]]; then
  echo "Run from repo root with .venv (science-graphrag CLI)." >&2
  exit 1
fi

PDF_COUNT="$(find "$DEFAULT_CORPUS" -type f -iname '*.pdf' | wc -l)"
echo "Pilot corpus: $DEFAULT_CORPUS"
echo "PDF files (recursive): $PDF_COUNT"
if [[ "$PDF_COUNT" -eq 0 ]]; then
  echo "No PDFs found; nothing to ingest." >&2
  exit 1
fi
if [[ "$PDF_COUNT" -lt 10 ]]; then
  echo "Warning: pilot checklist targets ~10–50 PDFs; found $PDF_COUNT." >&2
elif [[ "$PDF_COUNT" -gt 50 ]]; then
  echo "Warning: more than 50 PDFs; consider a subset for Wave D." >&2
fi

if [[ "${PILOT_DRY_RUN:-0}" == "1" ]]; then
  echo "PILOT_DRY_RUN=1 — skipping ingest."
  exit 0
fi

echo "Starting ingest-corpus …"
PROGRESS_FILE="${INGEST_PROGRESS_FILE:-eval/results/ingest-progress-wave5.jsonl}"
EXTRA_ARGS=(--continue-on-error --per-file-timeout-s 900 --progress-file "$PROGRESS_FILE")
if [[ "${INGEST_RESUME:-0}" == "1" ]]; then
  EXTRA_ARGS+=(--resume)
fi
if [[ "${INGEST_SKIP_EXISTING_SHA:-0}" == "1" ]]; then
  EXTRA_ARGS+=(--skip-existing-sha)
fi
# Prefer line-buffered output so progress logs appear immediately:
#   stdbuf -oL .venv/bin/science-graphrag ingest-corpus ... | tee ingest.log
if command -v stdbuf >/dev/null 2>&1; then
  stdbuf -oL .venv/bin/science-graphrag ingest-corpus "${EXTRA_ARGS[@]}" "$DEFAULT_CORPUS"
else
  .venv/bin/science-graphrag ingest-corpus "${EXTRA_ARGS[@]}" "$DEFAULT_CORPUS"
fi
echo "Done. Review dedup audit above; merge duplicates per docs/runbooks/deploy.md if needed."
echo "Verify Qdrant coverage: .venv/bin/python scripts/report_qdrant_work_coverage.py --min-works 16"
