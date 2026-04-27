# Spike: subprocess / job isolation for heavy LangGraph agent turns

**Status:** design note only (Phase 4 optional follow-up). No production wiring.

## Problem

Sync `invoke_graph_with_deadline` uses a process-local `ThreadPoolExecutor`. After a **response deadline**, the client stops waiting but the worker thread may continue LLM/tool work. Threads share memory and provider quotas; they do not give hard isolation or kill semantics for runaway turns.

## Option A — subprocess worker

- Spawn a short-lived child process per turn (or pooled workers) that runs `graph.invoke` with a serialized initial state.
- Parent uses IPC timeout; on expiry, **SIGTERM/SIGKILL** the child to stop CPU (provider HTTP may still complete in the child until killed).
- **Pros:** strongest containment for local CPU and Python-side loops.
- **Cons:** cold start, large pickle/msgpack of LangGraph state and tool closures, Neo4j/Qdrant clients must be recreated in child or accessed via RPC, OpenTelemetry context propagation across process boundary is non-trivial.

## Option B — job queue (Celery / Dramatiq)

- Enqueue agent turn; API polls or subscribes for result with deadline.
- Worker process can be recycled independently.
- **Cons:** same serialization and auth/session concerns; higher operational complexity than in-process pool tuning.

## Option C — stay in-process (current Phase 4)

- Bound `agent_graph_invoke_max_workers`, lower LangChain `max_retries`, cooperative `react_chat_response_budget_cutoff`, and measure post-deadline completion via `agent.graph_invoke_finished_after_response_deadline`.

## Recommendation

Defer A/B until multi-tenant fairness or runaway-turn incidents justify the operational cost. Prefer C plus provider-side rate limits and horizontal scaling of API workers with conservative per-process pools.
