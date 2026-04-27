# Phase 5B — advanced quota scope (deferred)

**Status:** deferred / not part of Phase 5 v1 stabilization (2026-04-27).

Phase 5 v1 delivers optional **cluster-wide** LLM concurrency using Redis ZSET leases with caps aligned to existing `llm_concurrency_*` pool settings (see ADR [025-llm-distributed-quota-redis.md](../adr/025-llm-distributed-quota-redis.md)).

The following items remain **explicitly out of scope** for v1 and require a separate design + rollout if needed:

1. **Per-provider or per-model global caps** — today the quota key is derived from the logical pool name (`translation`, `claims`, …), not from the resolved model id or provider hostname. A future change would introduce additional Redis namespaces or composite keys and likely new settings fields.
2. **Workspace- or tenant-level fairness** — v1 has no notion of fair share between tenants; enforcement is a single global cap per pool. Fairness policies (weighted round-robin, per-tenant sub-caps, etc.) need policy objects and possibly queueing semantics beyond the current lease acquire loop.
3. **Lease heartbeat / refresh** — v1 uses a fixed lease TTL without mid-call refresh; operators must size `llm_distributed_quota_lease_seconds` above worst-case LLM duration or accept rare over-cap when leases expire before calls end (documented in settings field description and runbook).

**Recommendation:** treat Phase 5B as a follow-up milestone with its own ADR if any of the above becomes a production requirement; do not expand Phase 5 v1 stabilization scope without capacity planning for Redis hot keys and observability.
