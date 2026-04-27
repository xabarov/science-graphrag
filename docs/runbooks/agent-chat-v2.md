# Agent Chat v2 (`POST /v2/agent/query`) — production runbook

## Release gate (merge / staging)

1. **Unit + contract (no API keys required)**
   - `pytest tests -m "not integration" -q`
   - `python -m eval.chat_agent` (or `.venv/bin/python -m eval.chat_agent`)

2. **Live API (optional, staging keys + stack)**
   - Set `AGENT_LIVE_BASE` (e.g. `http://127.0.0.1:8787`) and run  
     `pytest tests/live/test_agent_v2_http_optional.py -m live_api -q`
   - For CH4 compaction parity: `AGENT_LIVE_GATE_CH4=1` (see `scripts/live_check/http_suite.py`).

3. **SSE / reverse proxy**
   - Disable response buffering for SSE (`proxy_buffering off` on nginx, or equivalent).
   - `read_timeout` must exceed worst-case `SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS` (wall clock for one full LangGraph turn).

## Configuration

| Variable | Purpose |
|----------|---------|
| `SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS` | Max **wall-clock** seconds for one sync `invoke` or one SSE stream collection (default 120). |
| `SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND` | `memory` (single worker) or `redis` (multi replica). |
| `SCIENCE_GRAPHRAG_AGENT_TURN_POLICY_*` | Coordinator classifier rollout (`rules_v0` / `hybrid_v1` / `llm_v1`). |

**Note:** On deadline, the client receives `agent_turn_deadline_exceeded` (sync JSON `warnings` or SSE `error` with `code`). The worker thread may still finish the underlying `invoke` after the client disconnects; scale workers accordingly.

## Health

`GET /health` returns:

- `agent_session_memory_backend`: effective backend (`redis` or `memory`).
- `agent_session_memory_configured`: value from settings before fallback.

If configured `redis` but effective `memory`, Redis was unreachable at startup — fix Redis before relying on multi-turn sessions across replicas.

## Observability

- Root span: `agent.query` (sync and SSE).
- Child spans: `agent.turn_policy.llm` (when LLM classifier runs), `agent.supervisor.route_llm`.
- Event: `agent.supervisor.invalid_route_token` when the supervisor model did not return an exact route token (safe fallback to writer).
- `tool_trace` synthetic step `coordinator_gate` includes `duration_ms` from coordinator classification when measured.

## Rollout notes

See [`docs/analysis/agent-chat-prod-rollout-2026-04-27.md`](../analysis/agent-chat-prod-rollout-2026-04-27.md) for classifier / semantic fast-route / legacy runtime.
