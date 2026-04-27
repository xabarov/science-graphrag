# Runbook: distributed LLM quota (Redis, Phase 5)

## Purpose

When multiple API workers share one LLM provider, per-process semaphores are not enough. With `SCIENCE_GRAPHRAG_LLM_DISTRIBUTED_QUOTA_ENABLED=true`, the same numeric pool limits (`llm_concurrency_*`) are also enforced **globally** via Redis ZSET leases (see ADR [025-llm-distributed-quota-redis.md](../adr/025-llm-distributed-quota-redis.md)).

## Prerequisites

- `SCIENCE_GRAPHRAG_REDIS_URL` reachable from every worker (same URL as ingest bus / optional session backend).
- Operators saved LLM advanced settings or set env vars (see `.env.example` Phase 5 block).

## Enable

1. Confirm Redis: `redis-cli -u "$SCIENCE_GRAPHRAG_REDIS_URL" PING`.
2. Set `SCIENCE_GRAPHRAG_LLM_DISTRIBUTED_QUOTA_ENABLED=true` (or toggle in Settings UI advanced section) and save.
3. Optionally tune `SCIENCE_GRAPHRAG_LLM_DISTRIBUTED_QUOTA_KEY_PREFIX` if multiple environments share one Redis.
4. Restart API workers so all processes pick up the flag.

## Monitor

- Redis keys: `{prefix}:z:{pool}` (sorted set; members are UUID lease tokens, scores are expiry ms).
- Traces: span event `llm.distributed_quota.acquire_finished` with `llm.distributed_quota.fail_open` = `1` when Redis failed and the request proceeded without global gating.
- Logs: `llm distributed quota fail-open` warnings on Redis errors.

## Redis outage behavior

**Fail-open:** if Redis is unavailable, LLM calls proceed with **process-local** limits only; availability is preferred over strict global caps. Investigate Redis and re-enable when healthy.

## Acquire timeout

If operators see `DistributedQuotaAcquireTimeout`, global slots are saturated for longer than `llm_distributed_quota_acquire_timeout_seconds`. Options: raise pool caps, add workers (does not raise global cap), or increase acquire timeout (does not add provider capacity).

## Lease TTL (v1)

`llm_distributed_quota_lease_seconds` is a **safety TTL** for stale workers and is **not** refreshed while an LLM call is in flight. Size it above realistic worst-case call duration for your pools; if it is too short, an in-flight call can outlive its lease and another process may acquire (rare global over-cap). Heartbeat/refresh is deferred (see [llm-distributed-quota-phase5b-advanced-scope.md](../analysis/llm-distributed-quota-phase5b-advanced-scope.md)).

## Disable

Set `SCIENCE_GRAPHRAG_LLM_DISTRIBUTED_QUOTA_ENABLED=false` and restart workers. Stale ZSET members expire automatically via score-based pruning and lease TTL.
