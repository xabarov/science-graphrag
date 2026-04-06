#!/usr/bin/env bash
# Wave D KPI: p50/p95 for GET /v1/works and POST /v1/query (live API).
# Usage: BASE=http://127.0.0.1:8787 N=40 ./scripts/pilot_measure_latency.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "Need repo-root .venv with Python." >&2
  exit 1
fi
exec .venv/bin/python "$ROOT/scripts/pilot_measure_latency.py"
