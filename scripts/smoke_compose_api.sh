#!/usr/bin/env bash
# Build and start compose stack; wait for API /health and GET /v1/works on port 8787.
# Usage from repo root: ./scripts/smoke_compose_api.sh
# Override: SMOKE_API_URL=http://127.0.0.1:8787

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export COMPOSE_HTTP_TIMEOUT="${COMPOSE_HTTP_TIMEOUT:-180}"
docker compose up -d --build

API_URL="${SMOKE_API_URL:-http://127.0.0.1:8787}"
echo "Waiting for ${API_URL}/health ..."
for i in $(seq 1 90); do
  if curl -sf "${API_URL}/health" >/dev/null 2>&1; then
    echo "health: ok"
    break
  fi
  if [[ "$i" -eq 90 ]]; then
    echo "Timeout waiting for health." >&2
    docker compose ps >&2
    docker compose logs --tail 80 web >&2 || true
    docker compose logs --tail 80 api >&2 || true
    exit 1
  fi
  sleep 2
done

curl -sf "${API_URL}/v1/works?limit=1" >/dev/null
echo "GET /v1/works: ok"
echo "Compose API smoke passed."
