#!/usr/bin/env bash
# Wave D pilot: ingest the default CV object-detection corpus (31 PDFs).
# Prereq: docker compose up -d; .env with DB URLs and optional LLM keys.
# Override directory: PILOT_CORPUS_DIR=/path/to/pdfs ./scripts/pilot_ingest_cv_corpus.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

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

echo "Ingesting: $DEFAULT_CORPUS"
.venv/bin/science-graphrag ingest-corpus "$DEFAULT_CORPUS"
