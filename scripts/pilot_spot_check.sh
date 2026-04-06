#!/usr/bin/env bash
# Wave D citation spot-check (N queries against live API).
# Usage: BASE=http://127.0.0.1:8787 ./scripts/pilot_spot_check.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  echo "Need repo-root .venv." >&2
  exit 1
fi
exec .venv/bin/python "$ROOT/scripts/pilot_spot_check.py"
