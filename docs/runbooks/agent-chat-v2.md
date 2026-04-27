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
| `SCIENCE_GRAPHRAG_AGENT_CHAT_MAX_RETRIES` | LangChain HTTP retries for agent chat / routing (0–2, default 1). Lower reduces tail load after a response deadline. |
| `SCIENCE_GRAPHRAG_AGENT_CLASSIFIER_MAX_RETRIES` | HTTP retries for turn-policy classifier only (default 0). |
| `SCIENCE_GRAPHRAG_AGENT_GRAPH_INVOKE_MAX_WORKERS` | Cap concurrent sync `graph.invoke` threads per API process; `0` = auto (`min(16, max(4, cpu*2))`). Fixed at **first** use in process — restart workers to apply a new value. |
| `SCIENCE_GRAPHRAG_AGENT_MIN_LLM_HOP_RESERVE_SECONDS` | Wall-clock reserve before starting another LLM hop when the turn deadline is almost exhausted (cooperative cutoff). |
| `SCIENCE_GRAPHRAG_LLM_DISTRIBUTED_QUOTA_ENABLED` (and related `…_KEY_PREFIX`, `…_ACQUIRE_TIMEOUT`, `…_LEASE`) | Optional **cluster-wide** LLM caps via Redis (Phase 5); same numeric limits as `llm_concurrency_*` pools. See [`llm-distributed-quota.md`](llm-distributed-quota.md) and ADR [025-llm-distributed-quota-redis.md](../adr/025-llm-distributed-quota-redis.md). |

**Note:** On deadline, the client receives `agent_turn_deadline_exceeded` (sync JSON `warnings` and `product_markers`, or SSE `error` with `code`) **unless** the graph already produced a structured `final_answer` — then the SSE path **salvages** that payload: a `warning` frame plus a normal `final_answer` event with `warnings` / `product_markers` including `partial_after_deadline`, and `run_metadata.salvaged_after_deadline=true`. The worker thread may still finish the underlying `invoke` after the client disconnects; scale workers accordingly.

## Health

`GET /health` returns:

- `agent_session_memory_backend`: effective backend (`redis` or `memory`).
- `agent_session_memory_configured`: value from settings before fallback.

If configured `redis` but effective `memory`, Redis was unreachable at startup — fix Redis before relying on multi-turn sessions across replicas.

## Observability

- Root span: `agent.query` (sync and SSE).
- Child spans: `agent.turn_policy.llm` (when LLM classifier runs), `agent.supervisor.route_llm`.
- Event: `agent.supervisor.invalid_route_token` when the supervisor model did not return an exact route token (safe fallback to writer).
- Event: `agent.graph_invoke_deadline_exceeded` when sync `fut.result(timeout=…)` fires (`worker_may_continue=true`, `deadline_kind=response_only`).
- Event: `agent.graph_invoke_finished_after_response_deadline` when the worker thread **later** completes `graph.invoke` after that deadline (attributes: `lag_seconds`, `timeout_seconds`, `trace_id_hex`). Also logged at INFO. Process counter `graph_invoke_completed_after_deadline_total()` is for tests/diagnostics.
- Event: `agent.response_budget_precheck_cutoff` when cooperative cutoff skips a new LLM hop (supervisor specialists and single-agent ReAct).
- `tool_trace` synthetic step `coordinator_gate` includes `duration_ms` from coordinator classification when measured.

## Rollout notes

See [`docs/analysis/agent-chat-prod-rollout-2026-04-27.md`](../analysis/agent-chat-prod-rollout-2026-04-27.md) for classifier / semantic fast-route / legacy runtime.

**Architecture / future work:** [`docs/analysis/chat-agent-system-roadmap-2026-04-26.md`](../analysis/chat-agent-system-roadmap-2026-04-26.md) (slim canonical: simplified graph, `tool_search`, context compaction).
