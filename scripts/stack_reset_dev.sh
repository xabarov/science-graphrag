#!/usr/bin/env bash
# Dev-only: bring vector index and graph back in sync after Neo4j wipe or Qdrant drift.
# Requires repo .venv and .env with SCIENCE_GRAPHRAG_* URLs (same as compose port mappings).
# Review commands before running; Postgres is NOT truncated here (see deploy.md).

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/science-graphrag ]]; then
  echo "Missing .venv/bin/science-graphrag — create venv and pip install -e ." >&2
  exit 1
fi

echo "1) Neo4j: wiping all nodes (science-graphrag neo4j-wipe)"
.venv/bin/science-graphrag neo4j-wipe

echo "2) Qdrant: recreate empty chunks collection (science-graphrag qdrant-recreate-collection)"
.venv/bin/science-graphrag qdrant-recreate-collection

echo "Done. Re-run ingest. To also clear SQL document rows, run manually against Postgres:"
echo "  TRUNCATE ingestion_runs, documents RESTART IDENTITY CASCADE;"
echo "(Only if you use the same DB for dev.)"
