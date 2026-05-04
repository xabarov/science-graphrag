# Agent chat production rollout notes (2026-04-27)

## Coordinator (`TurnPolicy`)

- **Default:** `SCIENCE_GRAPHRAG_AGENT_TURN_POLICY_CLASSIFIER=rules_v0` — deterministic/heuristic only.
- **Hybrid:** `hybrid_v1` + `SCIENCE_GRAPHRAG_AGENT_TURN_POLICY_LLM_ENABLED=true` — LLM only on fuzzy `rules_v0` reasons; requires API key.
- **Full LLM:** `llm_v1` — narrow deterministic guardrails, then structured LLM with confidence threshold.

Tune `SCIENCE_GRAPHRAG_AGENT_TURN_POLICY_CONFIDENCE_THRESHOLD` using staging traffic and `eval/chat_agent` + live gates before promoting defaults.

## Supervisor semantic fast route

`SCIENCE_GRAPHRAG_AGENT_SEMANTIC_QUERY_FAST_ROUTE=true` skips one supervisor LLM routing hop when heuristics allow. Enable only after latency/regression checks (see `Settings` field description).

## Legacy runtime

`SCIENCE_GRAPHRAG_AGENT_RUNTIME=retrieval_v1` keeps the pre-supervisor path. Prefer `langgraph_supervisor_v1` (or project default) for new deployments; sunset `retrieval_v1` when no client depends on it.

## Metrics (logs)

Successful SSE runs emit a structured log record `agent_query_completed` with `agent_metrics` payload (`duration_ms`, `classifier`, `tool_policy`, `conversation_intent`, flags). Ship these to your log aggregator for p95 / error-rate dashboards.

**Architecture context:** [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) (slim canonical: simplified graph + future `tool_search` / compaction).
