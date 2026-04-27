# ADR 025: Cross-worker LLM concurrency via Redis (Phase 5)

**Status:** Accepted  
**Date:** 2026-04-27

## Context

Process-local `threading.Semaphore` pools ([`science_graphrag/llm/concurrency.py`](../science_graphrag/llm/concurrency.py)) cap LLM calls per API worker only. Multiple `uvicorn` workers or separate ingest/agent processes can still exceed operator-intended **global** concurrency toward the same provider.

Phase 5 of [llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md](../analysis/llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md) requires optional **distributed** enforcement.

## Decision

1. **Algorithm:** Use a **sorted-set (ZSET) lease registry** per logical pool, not a separate integer counter plus lease keys (avoids leaked counters if a process dies between `INCR` and lease `SET`).  
   - Members: unique **tokens** (UUID).  
   - Scores: expiry time in **milliseconds** since epoch.  
   - **Acquire (Lua):** `ZREMRANGEBYSCORE` up to `now_ms`; if `ZCARD < cap`, `ZADD` token with score `now_ms + ttl_ms`, return success; else return failure.  
   - **Release (Lua):** `ZREM` token.  
   - Expired members are pruned on acquire; TTL is a safety net if a worker dies without release.

2. **Cap source:** The distributed cap equals the same numeric limit as the process-local pool: `pool_concurrency_limit(settings, pool_name)` (same `llm_concurrency_*` settings). Operators therefore configure **one** number that applies **cluster-wide** when distributed quota is enabled.

3. **Ordering:** **Acquire process-local semaphore first, then distributed slot.** Rationale: avoid hammering Redis when the local worker is already saturated; global budget is still enforced before the guarded LLM call runs.

4. **Redis unavailable:** **Fail-open** — skip distributed acquire/release, log warning, emit span event `llm.distributed_quota.fail_open`. Availability beats strict quota when Redis is down.

5. **Acquire timeout:** If no slot becomes available within `llm_distributed_quota_acquire_timeout_seconds`, raise `DistributedQuotaAcquireTimeout` after releasing the **local** semaphore was not acquired yet — actually local is held first: on timeout we must **release local** before re-raising. Implemented in [`llm_pool_slot`](../../science_graphrag/llm/concurrency.py): distributed acquire runs while holding local; on timeout, release local in `except` path then raise.

6. **Keys:** `{llm_distributed_quota_key_prefix}:z:{sanitized_pool}` where `sanitized_pool` is `[a-z0-9_]+` derived from the pool name.

7. **Subprocess / true cancellation:** Out of scope; see [agent-graph-subprocess-isolation-spike-2026-04-27.md](../analysis/agent-graph-subprocess-isolation-spike-2026-04-27.md).

## Consequences

- Requires reachable Redis when `llm_distributed_quota_enabled=true` (same `redis_url` as ingest bus / session backend).  
- Adds per-acquire Redis round-trips (Lua `EVALSHA` after script load); keep socket timeouts short.  
- **Per-model / per-workspace fairness** deferred to a future ADR.  
- Runbook: [`docs/runbooks/llm-distributed-quota.md`](../runbooks/llm-distributed-quota.md).

## Residual risks (v1)

- **Lease TTL without refresh:** each acquire sets a ZSET member with score `now + lease_ms`. There is no heartbeat; if a single LLM HTTP call exceeds `llm_distributed_quota_lease_seconds`, the member may expire while the call is still running, allowing another worker to acquire (rare **hidden over-cap**). Mitigation: set lease comfortably above worst-case provider latency; future Phase 5B may add refresh.  
- **Observability:** sync paths and the async translation SSE path both emit `llm.distributed_quota.acquire_finished` after distributed acquire; Redis fail-open emits `llm.distributed_quota.fail_open` (see runbook).
