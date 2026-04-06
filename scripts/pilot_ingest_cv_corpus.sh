#!/usr/bin/env bash
# Wave D pilot: ingest the default CV object-detection corpus (31 PDFs).
# Prereq: docker compose up -d; .env with DB URLs and optional LLM keys.
# Override directory: PILOT_CORPUS_DIR=/path/to/pdfs ./scripts/pilot_ingest_cv_corpus.sh
# Dry run (count only): PILOT_DRY_RUN=1 ./scripts/pilot_ingest_cv_corpus.sh

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
.venv/bin/science-graphrag ingest-corpus "$DEFAULT_CORPUS"
echo "Done. Review dedup audit above; merge duplicates per docs/runbooks/deploy.md if needed."
