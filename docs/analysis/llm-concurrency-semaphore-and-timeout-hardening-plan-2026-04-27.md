# LLM concurrency, semaphore, and timeout hardening plan (2026-04-27)

**Status:** phased hardening plan (Phases 2–4 implemented in-repo; Phase 5 v1 distributed quota implemented — see Phase 5 section below).

**Primary goal:** make LLM concurrency control and timeout behavior consistent, enforceable, observable, and configurable from the settings UI for both:

- ingestion-time LLM usage;
- agent/query-time LLM usage.

**Secondary goal:** introduce defaults that are intentionally generous, close to the upper end of current practical limits, while still avoiding obviously unsafe behavior such as unbounded burst fan-out, misleading timeout semantics, or agent timeouts that only stop waiting but not the underlying load.

**Motivation:** the current codebase already has partial timeout protection and partial concurrency controls, but they are fragmented:

- there is a declared semaphore map in `science_graphrag/utils/llm_semaphore.py`, but it is not actually wired into the main production call paths;
- transport timeouts exist in many places, but the timeout model is not unified;
- one timeout API (`run_extraction(..., timeout_seconds=...)`) looks stronger than it really is;
- the current settings UI only exposes base URL, model, temperature, and one generic timeout, not the real concurrency/deadline knobs needed to operate the system safely.

This document proposes a best-practice architecture and a phased rollout that minimizes risk while making the system operationally honest.

---

## 1. Executive summary

The recommended target model has four layers:

1. **Named concurrency pools** for LLM calls, enforced in code rather than only declared in config.
2. **Two timeout layers** for every important LLM path:
   - **transport timeout** for one HTTP request;
   - **operation deadline** for the whole logical step, including retries and fallbacks.
3. **Process-local enforcement plus optional distributed limit**:
   - per-process semaphores / capacity limiters (Phases 2–3);
   - optional Redis-backed **global** quotas (Phase 5 v1 — ADR [025-llm-distributed-quota-redis.md](../adr/025-llm-distributed-quota-redis.md)).
4. **Settings UI support** for advanced LLM controls:
   - operator-facing knobs for semaphore sizes and deadlines;
   - separate groups for ingestion and agent runtime;
   - defaults that are high enough for heavy research workflows, not only conservative dev defaults.

The main design change is this:

> Stop treating timeout and concurrency as incidental parameters on individual clients; make them an explicit runtime control plane.

---

## 2. Current-state diagnosis

## 2.1 What is already good

The current codebase already has several useful building blocks:

- explicit HTTP timeouts in many `OpenAI`, `httpx`, and `ChatOpenAI` clients;
- separate timeout knobs for some specialized paths:
  - `extraction_llm_timeout_seconds`,
  - `work_dedup_llm_timeout_s`,
  - `author_dedup_llm_timeout_s`,
  - `agent_turn_policy_classifier_timeout_seconds`,
  - `agent_step_timeout_seconds`;
- one real concurrency cap for reference extraction via `ThreadPoolExecutor(max_workers=...)`;
- a settings API and settings UI that already support runtime-persisted, secret-aware LLM configuration.

These are good foundations. This plan does not replace them; it normalizes them.

## 2.2 Main current gaps

The main problems are:

1. **Declared but unused semaphores**
   - `build_llm_semaphore_map(...)` exists, but the main ingestion and agent LLM call paths do not actually acquire from it.

2. **Misleading timeout contract**
   - `run_extraction(..., timeout_seconds=...)` records timeout metadata for tracing, but it does not override the timeout on an already-created extractor client.

3. **Fragmented timeout semantics**
   - some paths use transport timeout only;
   - some paths use outer wall-clock deadline only;
   - some paths mix retries and timeouts without a single overall operation budget.

4. **Agent timeout is not true cancellation**
   - the API returns in bounded time, but the underlying graph/LLM work may continue in a thread after the deadline.

5. **Settings UI is too narrow for operations**
   - it only exposes:
     - base URL,
     - model,
     - temperature,
     - one generic timeout.
   - it does not expose:
     - concurrency pools,
     - agent-specific deadlines,
     - ingestion-stage limits,
     - classifier timeout,
     - dedup LLM timeouts,
     - call budget separation between transport timeout and total deadline.

---

## 3. Target architecture (best practices)

## 3.1 One runtime control plane for LLM calls

Introduce one explicit runtime abstraction, conceptually:

- `LlmCallPolicy`
- `LlmConcurrencyPool`
- `LlmDeadlinePolicy`

Every production LLM call should resolve three things before execution:

1. **Which pool am I in?**
   - `ingestion_metadata`
   - `ingestion_references`
   - `ingestion_claims`
   - `ingestion_semantic`
   - `dedup_judge`
   - `agent_classifier`
   - `agent_chat`
   - `query_answer`
   - `idea_summary`

2. **What is my transport timeout?**
   - one HTTP request timeout.

3. **What is my total operation deadline?**
   - includes retries, compact fallback, split retry, or chained model attempts.

This makes behavior explicit and observable instead of relying on implicit per-client defaults.

## 3.2 Two-level timeout model

Every important LLM path should have:

### A. Transport timeout

This protects one outbound provider request:

- socket connect,
- read,
- provider stall,
- slow model response.

Example use:

- `OpenAI(..., timeout=transport_timeout_seconds)`
- `httpx.Client(timeout=transport_timeout_seconds)`
- `ChatOpenAI(..., timeout=transport_timeout_seconds)`

### B. Operation deadline

This protects the whole logical unit:

- retries,
- fallback prompt variants,
- compact schema fallback,
- split-batch retry,
- outer agent turn envelope.

This should be enforced outside the raw client call, with one wrapper that can fail the operation even if the inner code still has remaining retry budget.

### Why both are required

Transport timeout alone is not enough because retries can stretch wall-clock duration far beyond what operators expect.

Operation deadline alone is not enough because a single network call can still hang too long.

Best practice is to keep both:

- **transport timeout < operation deadline**
- retries must fit inside the total deadline budget.

## 3.3 Named concurrency pools, not one global integer

A single global `max_concurrent_llm_calls` is too blunt. Different traffic classes have different risk profiles:

- ingestion references can burst in parallel;
- claims extraction can fan out on big documents;
- agent classifier should stay lightweight and fast;
- agent chat turns are fewer but more expensive;
- dedup LLM judgments are secondary and should not starve primary user-facing traffic.

So use named pools with separate defaults and optional priorities.

### Recommended first-generation pools

- `references`
- `claims`
- `summary`
- `agent_classifier`
- `agent_chat`
- `dedup`
- `default`

If implementation simplicity matters, `summary`, `query_answer`, and `idea_assist` can share the same pool at first.

## 3.4 Enforce concurrency in the same execution model as the caller

Current code mixes:

- synchronous OpenAI clients,
- `ThreadPoolExecutor`,
- async API streaming,
- LangGraph invocation in worker threads.

Best practice here is:

- use **thread-safe process-local semaphores** or a small concurrency-gate abstraction that works for sync code;
- if an async caller needs to enter the same pool, wrap it in an async-compatible adapter;
- do not rely on an `asyncio.Semaphore` that never gets awaited by the actual call path.

In other words:

> The gate must live where the work actually happens.

That means the current `asyncio.Semaphore` map is directionally correct but not sufficient as the primary enforcement mechanism for sync extraction code.

## 3.5 Do not promise true cancellation unless it exists

For the agent runtime, outer deadlines are useful, but the system should not pretend they stop upstream provider load if they only stop waiting locally.

Best practice:

- keep the current deadline behavior for user experience;
- document it as **response deadline**, not full cancellation;
- separately reduce runaway continuation through:
  - bounded worker pools,
  - LLM concurrency pools,
  - shorter transport timeouts,
  - lower retry budgets inside agent subpaths.

Later, if needed, introduce cooperative cancellation or move expensive agent LLM work into cancellable subprocesses/jobs. That is a later phase, not required for the first hardening pass.

---

## 4. Target settings model

## 4.1 Replace one generic timeout with explicit knobs

Keep the existing top-level `extraction_llm_timeout_seconds` for backward compatibility during migration, but move toward this explicit model:

### Shared provider defaults

- `llm_transport_timeout_seconds`
- `llm_max_retries`

### Ingestion defaults

- `ingestion_llm_transport_timeout_seconds`
- `ingestion_llm_operation_deadline_seconds`
- `ingestion_llm_references_concurrency`
- `ingestion_llm_claims_concurrency`
- `ingestion_llm_semantic_concurrency`

### Agent defaults

- `agent_llm_transport_timeout_seconds`
- `agent_llm_chat_operation_deadline_seconds`
- `agent_turn_policy_classifier_timeout_seconds`
- `agent_llm_concurrency`
- `agent_turn_deadline_seconds`

### Dedup / secondary judgment defaults

- `dedup_llm_transport_timeout_seconds`
- `dedup_llm_operation_deadline_seconds`
- `dedup_llm_concurrency`

### Optional shared generic pools

- `llm_concurrency_default`
- `llm_concurrency_summary`

## 4.2 Backward-compatible mapping

During migration:

- keep `extraction_llm_timeout_seconds`;
- map it to both transport timeout and operation deadline when no newer fields are set;
- keep `extraction_llm_references_max_concurrency` as legacy alias;
- preserve current API behavior for existing settings clients.

This avoids breaking existing env setups and settings snapshots.

---

## 5. Recommended defaults

The user asked for defaults that are “closer to maximum” for now. That should not mean “use the absolute maximum values everywhere.” Best practice is:

- choose defaults in the upper half of the supported range;
- leave headroom for emergency tuning upward;
- avoid defaults that immediately saturate provider quotas or local worker pools.

Below are recommended **high-but-still-defensible** defaults for the next architecture pass.

## 5.1 Ingestion defaults

### Core

- `ingestion_llm_transport_timeout_seconds = 300`
- `ingestion_llm_operation_deadline_seconds = 420`
- `llm_max_retries = 2`

Rationale:

- 300s transport timeout gives large models enough room for big structured outputs;
- 420s total budget still leaves time for a retry or compact fallback without silently running forever.

### Pool sizes

- `ingestion_llm_references_concurrency = 6`
- `ingestion_llm_claims_concurrency = 6`
- `ingestion_llm_semantic_concurrency = 4`
- `llm_concurrency_default = 12`

Rationale:

- references and claims are the main parallelizable ingestion stages;
- semantic extraction is usually one document-level call and should not dominate the pool;
- `12` as a default generic pool is high enough for heavy workloads but not so high that one process immediately turns into a provider burst cannon.

### Specialized ingest-related timeouts

- `work_dedup_llm_timeout_s = 45`
- `author_dedup_llm_timeout_s = 45`
- `method_ingest_llm_adjudication_timeout_seconds = 45` (new explicit field recommended)

Rationale:

- dedup judgment prompts are narrower than full extraction prompts and should fail faster.

## 5.2 Agent defaults

### Core

- `agent_llm_transport_timeout_seconds = 180`
- `agent_llm_chat_operation_deadline_seconds = 240`
- `agent_turn_policy_classifier_timeout_seconds = 20`
- `agent_step_timeout_seconds = 300`

Rationale:

- transport timeout for agent chat can be lower than ingestion, because turns are interactive;
- 240s per expensive chat/model operation is generous;
- 20s for classifier is intentionally high for a classifier, but still bounded;
- 300s full turn deadline is high enough for multi-tool research workflows and still much safer than drifting toward the current hard max of 900.

### Pool sizes

- `agent_llm_concurrency = 8`
- `llm_concurrency_summary = 6`
- `dedup_llm_concurrency = 4`

Rationale:

- agent chat turns are heavier and more user-visible, so concurrency should be high but not unbounded;
- summary/idea/query-answer traffic can share a mid-sized pool;
- dedup judgments should not starve direct user requests.

## 5.3 Query-answer / idea-assist defaults

- `query_answer_llm_transport_timeout_seconds = 120`
- `query_answer_llm_operation_deadline_seconds = 150`
- `idea_assist_llm_transport_timeout_seconds = 180`
- `idea_assist_llm_operation_deadline_seconds = 240`

If implementation simplicity matters, these can inherit from:

- `agent_llm_transport_timeout_seconds`
- `llm_concurrency_summary`

for the first rollout.

## 5.4 Why not set everything to the current hard max

Using the configured max everywhere would be a bad default:

- `900s` per call or turn is too forgiving for failures;
- `32` generic parallel calls per process is too aggressive without stronger backpressure and quota awareness;
- the system currently lacks a fully reliable cancellation path, so huge defaults amplify tail risk.

The values above are intentionally generous, but they still preserve room for escalation when operators really need it.

---

## 6. Settings UI target shape

The current `SettingsPage` LLM panel should evolve from a simple “provider card” into:

1. **Provider**
2. **Concurrency & Pools**
3. **Deadlines & Timeouts**
4. **Agent Runtime**
5. **Advanced / Secondary**

## 6.1 Provider section

Keep the current fields:

- base URL
- model
- temperature
- API key

Add:

- enable/disable LLM
- provider mode / structured-output mode
- retry budget

## 6.2 Concurrency & Pools section

Expose operator-facing integer controls for:

- default pool
- ingestion references pool
- ingestion claims pool
- summary/idea/query-answer pool
- agent chat pool
- dedup pool

### UX behavior

- show defaults and effective values;
- display recommended range and hard bounds;
- allow reset-to-recommended;
- highlight “high fan-out” fields with helper text.

## 6.3 Deadlines & Timeouts section

Expose:

- shared transport timeout
- ingestion operation deadline
- agent chat operation deadline
- full agent turn deadline
- classifier timeout
- dedup LLM timeout

### UX rule

The form should validate:

- operation deadline must be greater than transport timeout;
- full turn deadline must be greater than agent chat operation deadline;
- classifier timeout must be lower than or equal to agent transport timeout unless explicitly overridden.

## 6.4 Agent Runtime section

Expose:

- `agent_step_timeout_seconds`
- `agent_turn_policy_classifier_timeout_seconds`
- `agent_turn_policy_llm_enabled`
- `agent_runtime`
- `agent_max_tool_calls`

This makes the agent behavior operable without editing env vars or config files.

## 6.5 Ingestion section

Extend the current ingestion settings beyond upload-size and claims-enabled:

- references concurrency
- claims concurrency
- semantic concurrency
- ingestion transport timeout
- ingestion operation deadline

This is important because ingestion load is operationally very different from interactive agent load.

---

## 7. Phased rollout plan

## Phase 0: Truthfulness and observability cleanup

**Goal:** make current behavior honest before changing semantics.

**Status (implementation):** Phase 0 is **in progress / landed in code** as of 2026-04-27: canonical span attributes + agent response-deadline labeling + ingestion timeout alignment in `run_extraction`; see `docs/architecture/observability-phoenix.md` §LLM runtime policy.

### Changes

1. Audit every LLM call path and classify it by pool name and timeout type.
2. Add tracing fields that distinguish:
   - `transport_timeout_seconds`
   - `operation_deadline_seconds`
   - `retry_budget`
   - `pool_name`
3. Mark current agent deadline as `response_deadline_seconds` where relevant.
4. Fix any misleading telemetry that implies a timeout is enforced when it is not.

### Sub-waves (execution order)

| Wave | Focus |
|------|--------|
| 0A | Audit matrix (table below) + scope allowlist for `PHOENIX_TRACE_SCOPE=extraction_llm` |
| 0B | `SpanAttributes.llm_runtime_policy_attributes` + Phoenix doc |
| 0C | Ingestion: `run_extraction` / orchestrator / semantic / claims / VL |
| 0D | Agent: `agent.query` attrs, `invoke_graph_with_deadline` event, SSE/sync deadline events |
| 0E | Dark paths: `llm.query_answer`, `llm.dedup.*`, `llm.idea_assist`, agent subgraph `llm.agent.*` policy attrs |
| 0F | Tests + doc sync |

### Audit matrix (major production LLM paths)

| Path | Span name(s) | Client / transport timeout | Outer deadline | `llm.pool_name` | `llm.timeout_contract` |
|------|----------------|-----------------------------|------------------|-----------------|-------------------------|
| Ingest metadata | `llm.metadata_extraction` | `Settings.extraction_llm_timeout_seconds` | none (per-file timeout is separate) | `metadata` | `transport_only` |
| Ingest authorships | `llm.authorships_extraction` | same | none | `metadata` | `transport_only` |
| Ingest references (chunks) | `llm.references_extraction` | same | none | `references` | `transport_only` |
| Ingest semantic | `llm.semantic_method_dataset` | same | none | `semantic` | `transport_only` |
| Ingest claims | `llm.claims_extraction` / compact | same | none | `claims` | `transport_only` |
| VL PDF | `llm.vl_pdf` | 300s per `post_chat_completions_json` call | none | `vl_pdf` | `transport_only` (+ `llm.transport_max_attempts`) |
| Work dedup LLM | `llm.dedup.same_work` | `work_dedup_llm_timeout_s` | none | `dedup` | `transport_only` |
| Author dedup LLM | `llm.dedup.same_author` | `author_dedup_llm_timeout_s` | none | `dedup` | `transport_only` |
| Method ingest adjudicate | `llm.method_ingest_adjudicate` | `min(45, extraction_llm_timeout_seconds)` | none | `dedup` | `transport_only` |
| Query grounded answer | `llm.query_answer` | `min(extraction_llm_timeout_seconds, 120)` | none | `query_answer` | `transport_only` |
| Idea assist | `llm.idea_assist` | `extraction_llm_timeout_seconds` | none | `idea_assist` | `transport_only` |
| Agent turn policy | `llm.agent.turn_policy` | `agent_turn_policy_classifier_timeout_seconds` | none | `agent_classifier` | `transport_only` |
| Agent supervisor route | `llm.agent.supervisor_route` | `extraction_llm_timeout_seconds` | none | `agent_chat` | `transport_only` |
| Agent specialists / single ReAct | `llm.agent.*` / `llm.agent.react_turn` | `extraction_llm_timeout_seconds` | none | `agent_chat` | `transport_only` |
| Agent turn (root) | `agent.query` | per-LLM child spans | `agent_step_timeout_seconds` (wait only) | — | `response_deadline_only` on **chain** via `agent.response_deadline_*` |

### Acceptance

- every major LLM call path emits a pool name and explicit timeout attributes;
- dashboards/logs can distinguish provider stall vs operation budget exhaustion.

## Phase 1: Real timeout enforcement model

**Goal:** make timeout parameters actually govern execution.

### Changes

1. Introduce one wrapper for sync extraction calls that applies:
   - transport timeout at client construction;
   - operation deadline around the logical extraction step.
2. Remove or deprecate misleading `run_extraction(..., timeout_seconds=...)` semantics unless it becomes enforceable.
3. Ensure fallback chains and retries consume one total deadline budget.
4. Normalize timeout naming across:
   - ingestion extraction,
   - dedup judges,
   - query answer,
   - idea assist,
   - agent classifier/chat.

### Acceptance

- timeout values in traces match real enforcement;
- one logical extraction step cannot exceed its declared total deadline without explicit outer override.

## Phase 2: Wire real concurrency pools

**Goal:** make semaphore-like controls operational.

### Changes

1. Replace unused/declarative-only semaphore usage with real gating in call paths.
2. Add pool acquisition in:
   - references extraction,
   - claims extraction,
   - semantic extraction,
   - dedup judgment,
   - agent classifier,
   - agent chat,
   - query-time answer,
   - idea assist.
3. Use process-local concurrency gates that actually work for the sync-heavy paths.
4. Ensure gates are released on exceptions and deadline failures.

### Acceptance

- operator can lower one pool and observe corresponding throughput reduction;
- references/claims/agent chat no longer burst independently without shared control.

## Phase 3: Settings API and UI expansion

**Goal:** expose the new controls safely to operators.

**Status (implementation): done (variant A, 2026-04-27).** Runtime overrides for fields that already exist on `Settings` are persisted as flat keys in the runtime `llm` JSON (same attribute names as env), merged via `SettingsService.build_runtime_settings()` → `Settings.model_copy(update=...)`. Ingestion-specific concurrency is editable in the LLM advanced panel (not moved to `PATCH /settings/ingestion` in v1).

**Delivered**

- **Backend:** `science_graphrag/settings/llm_advanced_fields.py` (keys, clamp, recommended defaults from `Settings` fields, cross-field validation); `SettingsService` snapshot adds `llm.advanced_controls` (per-key `persisted` / `effective`), `llm.recommended_advanced`, `non_secret_overrides` extended; `work_dedup.effective` reflects merged dedup LLM timeouts. `GET /v1/settings/schema` version **4** with grouped advanced field descriptors. `PATCH /v1/settings/llm` accepts optional nested `runtime_overrides` (`science_graphrag/api/settings_llm_runtime_patch.py`); invalid classifier vs transport or step vs classifier → **422**.
- **Frontend:** `ui/src/pages/SettingsPage/LlmSettingsPanel.jsx` — provider card unchanged; collapsible advanced section (concurrency / deadlines / agent runtime); restore from `recommended_advanced`; client-side validation (transport timeout, finite numerics, classifier ≤ transport, step ≥ classifier); draft connection test still uses form `timeout_seconds`. i18n: `ui/src/i18n/messages/en|ru/partSettings.js`.
- **Tests:** `tests/test_chat_llm_settings.py` (roundtrip + regression that provider-only PATCH keeps advanced); `tests/test_api_smoke.py` (snapshot keys, `runtime_overrides` 422).

**Deferred (not variant A / later phases)**

- Separate persisted **ingestion operation deadline** and **retry budget** knobs (§4.1); dedicated `PATCH /settings/ingestion` fields for references/claims/semantic concurrency only (§6.5) — optional follow-up.
- **“High fan-out”** helper copy in UI (§6.2) — can be added as short `FormHelperText` under pool fields.

### Backend

1. Extend `SettingsSnapshotResponse`, `SettingsSchemaResponse`, and runtime snapshot building.
2. Add persisted runtime overrides for:
   - pool sizes,
   - transport timeouts,
   - operation deadlines,
   - retry budget,
   - agent-specific timeouts.
3. Keep compatibility with the current `/settings/llm` and `/settings/ingestion` shapes, or version the API if needed.

### UI

1. Expand `LlmSettingsPanel` into multiple subsections.
2. Add an advanced mode with concurrency and deadline controls.
3. Show recommended defaults, current effective values, and validation rules.
4. Add “restore recommended defaults” and “test current draft” actions.

### Acceptance

- an operator can configure timeout and concurrency without touching env files;
- UI validation prevents obviously invalid combinations;
- **Variant A scope:** pool sizes, shared extraction transport timeout, agent step / classifier timeouts, dedup LLM timeouts, and agent runtime flags via `runtime_overrides`. Separate ingestion operation deadline, retry budget in settings UI, and ingestion-only PATCH for pool fields are deferred (see **Deferred** above).

## Phase 4: Agent timeout containment and worker hygiene

**Goal:** reduce post-timeout load leakage in the agent runtime.

**Status (implementation): done (2026-04-27).** True upstream cancellation is still out of scope; this phase tightens process-local containment, retries, cooperative cutoffs, and observability.

### Changes

1. Bound worker pool growth and LLM pool interaction more tightly.
2. Lower retry budgets for agent-only model calls.
3. Add stronger observability for “deadline returned to user but upstream still running”.
4. Optionally move expensive agent turns to cancellable subprocess/job isolation if needed.

### Delivered

- **Retries:** `Settings.agent_chat_max_retries`, `agent_classifier_max_retries`; `build_chat_model(..., max_retries=...)`; classifier uses dedicated retries; agent graph spans use `agent_chat_transport_max_attempts(settings)` instead of ingestion `EXTRACT_MAYBE_*` ([`science_graphrag/agent/llm/chat.py`](../science_graphrag/agent/llm/chat.py), nodes + [`supervisor.py`](../science_graphrag/agent/graph/supervisor.py), [`llm_turn_classifier.py`](../science_graphrag/agent/coordination/llm_turn_classifier.py)).
- **Graph thread pool:** `agent_graph_invoke_max_workers` (0 = auto); lazy `ThreadPoolExecutor` in [`invoke_timeout.py`](../science_graphrag/agent/graph/invoke_timeout.py); one-time WARNING if effective size differs from an already-created pool; [`runtime.py`](../science_graphrag/agent/runtime.py) passes `settings`.
- **Cooperative cutoff:** `agent_min_llm_hop_reserve_seconds`; `react_chat_response_budget_cutoff` in retrieval/graph `chat_node` ([`react_edges.py`](../science_graphrag/agent/graph/react_edges.py), specialist nodes).
- **Post-deadline observability:** `Future.add_done_callback` → span event `agent.graph_invoke_finished_after_response_deadline`, process counter, optional hook, INFO log (logging failures swallowed in callback); [`docs/runbooks/agent-chat-v2.md`](../runbooks/agent-chat-v2.md) updated.
- **Settings / UI / PATCH:** keys in [`llm_advanced_fields.py`](../science_graphrag/settings/llm_advanced_fields.py), [`settings_llm_runtime_patch.py`](../science_graphrag/api/settings_llm_runtime_patch.py), UI [`llmRuntimeOverrideKeys.js`](../ui/src/pages/SettingsPage/llmRuntimeOverrideKeys.js), i18n; `.env.example` lines for Phase 4.
- **Spike (no prod wiring):** [`docs/analysis/agent-graph-subprocess-isolation-spike-2026-04-27.md`](agent-graph-subprocess-isolation-spike-2026-04-27.md).

### Acceptance

- timed-out agent turns no longer create significant uncontrolled background pressure;
- provider usage after user-visible deadline becomes measurable and rare.

**Evidence:** lower LangChain `max_retries` on agent paths; bounded concurrent `invoke` threads; cooperative skip of further LLM hops near wall-clock end; measurable `lag_seconds` after response deadline (logs / span event / `graph_invoke_completed_after_deadline_total()`). Residual provider tail remains possible until true cancel or subprocess isolation (Phase 4 spike).

## Phase 5: Optional multi-worker / distributed quotas

**Goal:** coordinate limits across multiple API workers or hosts.

**Status (implementation): Phase 5 v1 done (2026-04-27).** Optional Redis **ZSET lease** registry (not a separate integer counter); cluster-wide cap matches the same `llm_concurrency_*` numeric limits as process-local pools. Translation SSE and sync `llm_pool_slot` paths share observability events (`llm.distributed_quota.acquire_finished`, `llm.distributed_quota.fail_open`).

### Delivered (v1)

- **Core:** [`science_graphrag/llm/redis_quota.py`](../science_graphrag/llm/redis_quota.py), [`science_graphrag/llm/concurrency.py`](../science_graphrag/llm/concurrency.py), [`science_graphrag/llm/pool_limits.py`](../science_graphrag/llm/pool_limits.py); settings in [`config.py`](../science_graphrag/config.py), [`settings/llm_advanced_fields.py`](../science_graphrag/settings/llm_advanced_fields.py), API patch in [`api/settings_llm_runtime_patch.py`](../science_graphrag/api/settings_llm_runtime_patch.py).
- **Async parity:** [`api/translation.py`](../science_graphrag/api/translation.py) acquires/releases distributed quota in a thread pool and emits the same acquire-finished span contract as sync paths.
- **Fail-open:** Redis client or `EVAL` errors → proceed without global cap; span `llm.distributed_quota.fail_open` + WARNING logs.
- **Settings UI / i18n:** advanced group + operator copy in [`ui/src/pages/SettingsPage/LlmSettingsPanel.jsx`](../ui/src/pages/SettingsPage/LlmSettingsPanel.jsx).
- **Tests:** unit + integration-style (`tests/llm/test_redis_distributed_llm_quota*.py`), API smoke for schema/snapshot/PATCH (`tests/test_api_smoke.py`), translation route (`tests/api/test_translation_distributed_quota.py`).

### Residual risks (v1)

- **Lease TTL:** no mid-call lease refresh; a call longer than `llm_distributed_quota_lease_seconds` can allow another worker to acquire (documented in ADR, runbook, and Settings field description).

### Deferred (Phase 5B)

- Per-provider / **per-model** global keys; **workspace- or tenant-level fairness**; lease heartbeat — see [`llm-distributed-quota-phase5b-advanced-scope.md`](llm-distributed-quota-phase5b-advanced-scope.md).

### Acceptance (v1)

- With live Redis and `llm_distributed_quota_enabled`, aggregate concurrency for a pool does not exceed the configured cap across worker-like contexts; with Redis errors, requests remain available (fail-open) and traces show fail-open.

---

## 8. Concrete implementation sketch

This is the minimum practical code direction, without a full rewrite:

1. Add a small runtime module such as:
   - `science_graphrag/llm/control_plane.py`

2. Define:
   - pool registry,
   - sync and async acquisition helpers,
   - timeout/deadline policy resolution.

3. Update these first-wave call paths:
   - `science_graphrag/ingestion/llm/extractor.py`
   - `science_graphrag/ingestion/llm/executor.py`
   - `science_graphrag/ingestion/llm/orchestrator.py`
   - `science_graphrag/ingestion/claims/extractor.py`
   - `science_graphrag/dedup/work_dedup_engine.py`
   - `science_graphrag/dedup/author_dedup_engine.py`
   - `science_graphrag/dedup/method_ingest_adjudicate.py`
   - `science_graphrag/agent/llm/chat.py`
   - `science_graphrag/agent/coordination/llm_turn_classifier.py`
   - `science_graphrag/retrieval/llm_answer.py`
   - `science_graphrag/agent/idea_workflow.py`

4. Update settings support in:
   - `science_graphrag/settings/service.py`
   - `science_graphrag/api/settings_models.py`
   - `science_graphrag/api/settings.py`
   - `ui/src/pages/SettingsPage/LlmSettingsPanel.jsx`

This keeps the first pass narrow and operationally meaningful.

---

## 9. Recommended first release scope

To avoid over-scoping, the first real fix release should include only:

1. honest timeout semantics;
2. real concurrency enforcement for:
   - references,
   - claims,
   - agent classifier,
   - agent chat,
   - query answer;
3. settings backend + UI for:
   - shared transport timeout,
   - ingestion deadline,
   - agent turn deadline,
   - classifier timeout,
   - pool sizes.

Do **not** block the first release on:

- distributed quotas,
- true cancellation of threaded agent work,
- full per-model fairness,
- a total refactor of every LLM client abstraction.

That smaller release already solves the biggest operational gaps.

---

## 10. Final recommendation

The best next move is not a broad rewrite. It is a phased hardening pass:

1. make timeout semantics truthful;
2. make concurrency controls real;
3. expose them in the settings UI;
4. keep defaults generous but not maximal.

The recommended operator-facing defaults for the first rollout are:

- `ingestion_llm_transport_timeout_seconds = 300`
- `ingestion_llm_operation_deadline_seconds = 420`
- `ingestion_llm_references_concurrency = 6`
- `ingestion_llm_claims_concurrency = 6`
- `ingestion_llm_semantic_concurrency = 4`
- `llm_concurrency_default = 12`
- `agent_llm_transport_timeout_seconds = 180`
- `agent_llm_chat_operation_deadline_seconds = 240`
- `agent_step_timeout_seconds = 300`
- `agent_turn_policy_classifier_timeout_seconds = 20`
- `agent_llm_concurrency = 8`
- `llm_concurrency_summary = 6`
- `dedup_llm_concurrency = 4`
- `work_dedup_llm_timeout_s = 45`
- `author_dedup_llm_timeout_s = 45`

These defaults are intentionally high, suitable for heavy ingestion and research-agent workloads, but still materially safer than treating the current hard maximum values as defaults.
