#!/usr/bin/env bash
# One-shot: recreate api with tool_use_summary off/on, run trace-review, regression compare.
set -euo pipefail
REPO="/home/roman/pyprojects/ML/Prod/science-graphrag"
cd "$REPO"
export AGENT_LIVE_BASE="${AGENT_LIVE_BASE:-dev}"
BASE_URL="${AGENT_LIVE_TRACE_URL:-http://127.0.0.1:18787}"
WS="${AGENT_LIVE_WORKSPACE_ID:-ws-pilot-od}"
COMPOSE=(docker compose -f docker-compose.dev.yml)

recreate_api() {
  local v="${1:?}"
  echo "[paired-e2] recreate api TOOL_USE_SUMMARY=${v}"
  SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED="${v}" "${COMPOSE[@]}" up -d api --no-deps
  echo "[paired-e2] waiting for api healthy..."
  for _ in $(seq 1 60); do
    st="$("${COMPOSE[@]}" ps api --format '{{.Status}}' 2>/dev/null || true)"
    if echo "$st" | grep -qi healthy; then
      echo "[paired-e2] api status: $st"
      sleep 5
      return 0
    fi
    sleep 3
  done
  echo "[paired-e2] ERROR: api not healthy in time" >&2
  exit 1
}

recreate_api 0
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$BASE_URL" \
  --workspace-id "$WS" \
  --suite default \
  --profile default \
  --out-json eval/results/trace-review-e2-baseline-summary-off-2026-05-12.json \
  --out-md eval/results/trace-review-e2-baseline-summary-off-2026-05-12.md

recreate_api 1
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$BASE_URL" \
  --workspace-id "$WS" \
  --suite default \
  --profile default \
  --out-json eval/results/trace-review-e2-candidate-summary-on-2026-05-12.json \
  --out-md eval/results/trace-review-e2-candidate-summary-on-2026-05-12.md

set +e
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/trace-review-e2-baseline-summary-off-2026-05-12.json \
  --candidate eval/results/trace-review-e2-candidate-summary-on-2026-05-12.json \
  --min-side-llm-cache-read-ratio 0.4 \
  --out-json eval/results/trace-regression-e2-tool-summary-2026-05-12.json \
  --out-md eval/results/trace-regression-e2-tool-summary-2026-05-12.md \
  --warn-is-pass
cmp_rc=$?
set -e
echo "[paired-e2] trace_regression_compare exit=${cmp_rc}"
echo "[paired-e2] done"
