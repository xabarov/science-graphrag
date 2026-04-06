#!/usr/bin/env bash
# Regenerate eval/results/benchmark-metrics-summary.* after LLM / benchmark runs.
# Pass-through args go to aggregate_benchmark_metrics.py

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "Need repo-root .venv." >&2
  exit 1
fi
exec .venv/bin/python scripts/aggregate_benchmark_metrics.py "$@"
