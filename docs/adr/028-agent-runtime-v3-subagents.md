# ADR 028: Agent runtime v3 — subagent foundation

**Status:** Accepted  
**Date:** 2026-05-06  
**Related:** ADR-020 (supervisor), ADR-027 (`agent_runtime` / `run_metadata`), roadmap §9.4 B0/B1, `docs/specs/agent-chat-v1.md`

## Context

SciGraph needs a first-class **subagent lifecycle** (spawn, bounded parallelism, terminal states, per-child observability) without fragmenting the product HTTP surface. OpenClaude-style **coordinator-mode** (explicit task IDs, async messaging) and **fork-mode** (cache-aligned inherited prefix) are different trade-offs; economics and existing `/v2` contracts must stay coherent.

## Decision

### HTTP / API shape

- **Canonical entrypoint remains `POST /v2/agent/query`** (JSON or SSE). No separate `/v3/agent/query` in this foundation wave.
- **Runtime selection** continues to use `Settings.agent_runtime` (ADR-027). A dedicated value **`langgraph_supervisor_v3`** marks runs that use v3 subagent observability and policies while the LangGraph wiring may still share the supervisor graph until a split is justified.
- **Product `run_kind` / `graph_id` attribution** for v3 runs is **`supervisor_specialists_v3` / `supervisor_graph_v3`** so traces and `trace-review-v1` can distinguish v3 from v1 without a second HTTP route.

### Fork-mode vs coordinator-mode

- **Default for v3 side work:** **fork-mode** — child prompts inherit the parent’s stable system/tool surface and thinking configuration so OpenRouter-style **prompt cache** reuse stays predictable (same tool array shape, no child-specific `max_output_tokens` overrides in the fork contract; no alternate “thinking” profile for the child unless explicitly specified later in a product scenario).
- **Coordinator-mode** (explicit task registry, `send_message` / `task_stop`, stronger async UX) is **out of scope** for this foundation ADR and is only allowed behind a **future explicit product case** + separate ADR when user-visible “continue specialist” semantics are required.

### When to spawn; sync vs background; merge; failures

- **Spawn decision (policy-level):** spawn a bounded child run when work is isolatable (read-only fan-out, verification, corpus slice) and the parent should not interleave tool transcripts; do **not** spawn for trivial single-tool hops that the main graph already models. Exact automation (which nodes call `spawn_subagent`) is deferred; this ADR defines the **contract** and **runtime primitive**.
- **Sync vs background:** default child execution is **synchronous within the parent turn** (same HTTP/SSE request). **Background** children (outlive the parent response) are **not** implemented in this wave; reserve `execution_mode` in task spec for a later train.
- **Merge contract (parent):** only structured carry-back (summary + optional citations + provenance) merges into the parent transcript; full child message dumps stay in **sidechain** artifacts (see §6.1.5 / `agent_sidechain_transcripts_*`). **Implemented (2026-05-07):** `<task-notification>` user-role `HumanMessage` rows + `run_metadata.subagent_task_notifications` + bounded `SubagentCarryBack` payload (`science_graphrag/agent/subagents/notification.py`, `lifecycle.py`). **Implemented (2026-05-07, Epic B2):** typed `specialist_results_v3` merge (`science_graphrag/agent/subagents/specialist_results_v3.py`) + optional `claim_verification` child (`claim_verification_runtime.py`, feature-flagged).
- **Failure taxonomy (child run):**
  - **Terminal states (machine):** `succeeded` | `failed` | `cancelled` | `timed_out`.
  - **Semantic causes (telemetry / UI):** map into `failure_code` optional string, including at minimum `timeout`, `partial`, `cancelled`, `tool_denied` (aligns with roadmap §9.4 B0). `failed` is the generic bucket when no finer code is set.

### Prompt-cache contract (fork-mode)

- Child fork inherits the **same catalog tool bindings shape** and **same thinking / reasoning config** as the parent turn unless a future ADR defines an exception list.
- **Do not** vary `max_output_tokens` (or equivalent) inside the forked child for cache-key stability; token pressure is enforced by **turn budgets** and future per-child caps (B3), not by silent parameter drift on the fork.

### Observability

- Every parent turn exposes **`parent_turn_id`** (UUID) in `run_metadata` and on **`subagent_*` SSE events** where a child leg is active.
- Each completed or terminal child row in **`run_metadata.subagent_runs`** includes: `subagent_id`, `parent_turn_id`, `spawn_reason`, `terminal_state`, `latency_ms` (when measurable), `tokens` / `cost_usd_estimate` (nullable until per-child usage attribution exists).
- **Lifecycle extras (v3 only, feature-flagged):** optional SSE `subagent_heartbeat` while a routing leg is active; `subagent_progress_label` (throttled, deterministic from last tool progress — not an LLM AgentSummary fork yet); mandatory **subagent JSONL sidechain** rows when `agent_sidechain_transcripts_enabled` (path `subagent/<parent_turn_id>/<subagent_id>.jsonl` under `agent_sidechain_transcripts_dir`); `run_metadata.subagent_observability_lane` (`fork_v3_enhanced` vs `legacy_routing_sse_only`) documents rollback / lane selection.

### Rollback / lane selection

- **`agent_subagent_lifecycle_enhanced_enabled`:** when `false` under `langgraph_supervisor_v3`, observability falls back to routing-only SSE (`legacy_routing_sse_only`) without task-notification injection or sidechain lifecycle rows.
- **Coordinator benchmark stub:** `agent_subagent_coordinator_lane_stub_enabled` injects a synthetic `HumanMessage` marker for fork-vs-coordinator compare harnesses without implementing coordinator runtime.

## Consequences

- Clients keep one URL; v3 is discovered via `run_metadata.agent_runtime`, `run_kind`, `graph_id`, and `subagent_runs`.
- Benchmarks comparing fork vs coordinator: **synthetic decision artifact** ships as `eval/chat_agent/subagent_runtime_fork_vs_coordinator_bench.py` (+ `eval/results/subagent-runtime-fork-vs-coordinator-bench.{json,md}` when executed); operators should replace lanes with real `agent_trace_review` exports for production gates.
- `langgraph_supervisor_v3` currently uses the same compiled supervisor graph as v1 where no v3-only nodes exist yet; divergence is expected in a later train.

## R4 vertical slice note (2026-05-13)

The first real shipped slice on top of this ADR is intentionally narrow:

- one explicit spawned child type is treated as canonical for the slice: `corpus_explore`;
- fanout remains bounded to `max_parallel_subagents=1` for the product lane;
- execution is sync / in-process only;
- every spawned row must carry `task_id`, `task_type`, `description`, `terminal_state`,
  `merge_provenance`, and `output_pointer`;
- Ask/SSE may still emit routing-leg `subagent_*` events, but spawned children now also surface
  as explicit lifecycle rows (`kind="spawned"`) in both `run_metadata.subagent_runs` and live SSE
  when terminal metadata is available.

This is a vertical slice, not a coordinator-runtime launch. Background continuations, cross-child
messaging, and `fanout > 1` remain deferred to a future ADR / wave.

## Deferred (explicitly not this ADR)

- `claim_verification`, `corpus-explore`, `research-plan` subagents; registry loader; dynamic schema transport.
- LLM-driven **AgentSummary-style** `subagent_progress_label` (current implementation is deterministic + throttled; no cache-safe forked micro-LLM yet).
- Full per-child token/cost attribution (requires message tagging or subgraph accounting).
