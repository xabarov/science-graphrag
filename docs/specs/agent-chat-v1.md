# Agent Chat API v1 (research workspace)

**Status:** implemented — **Wave A** (CH1+CH2+CH3) + **Wave B** (CH4 v1 session: `thread_id`, `history_digest`, turn digest, SSE `context_compacted`, `session_init` in `tool_trace`) + **Wave Next** (optional **Redis** session persistence via `SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND`, CH5 v1 compaction metadata, sync `run_metadata.compaction` parity).  
**HTTP:** `POST /v2/agent/query`  
**Modes:** JSON (`Accept: application/json`) or SSE (`Accept: text/event-stream`)

### Agent runtime v3 foundation (Train T3 B0/B1 skeleton)

**Normative:** ADR-028. **HTTP:** still **`POST /v2/agent/query`** — no `/v3` route in this wave. **Selector:** `SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3` (same response envelope as v2; distinct `run_kind` / `graph_id` for attribution).

| Field / event | Purpose |
|---------------|---------|
| `run_metadata.parent_turn_id` | UUID for one parent turn; stable across all child legs in that request. |
| `run_metadata.subagent_runs` | List of completed child legs: `subagent_id`, `parent_turn_id`, `spawn_reason`, `terminal_state` (`succeeded` \| `failed` \| `cancelled` \| `timed_out`), optional `latency_ms`, optional `tokens` / `cost_usd_estimate` (often null until per-child usage is wired). |
| `run_metadata.max_parallel_subagents` | Server fanout cap for explicit `spawn_subagent` (see Settings). |
| `run_metadata.subagent_task_notifications` | Optional list of structured completion payloads mirrored from `<task-notification>` `HumanMessage` rows (same contract as SSE `subagent_task_notification`). |
| `run_metadata.specialist_results_v3` | Optional typed merge payload: `schema_version`, `legs[]` (parent_tool + `claim_verification` child rows), `merge` (`evidence_origin`, `confidence`, `conflict`, `writer_directive`, `partial_failure`). |
| `run_metadata.claim_verification_results` | Optional list mirrored from transcript `HumanMessage` rows (`kind="claim_verification_result"`): `subagent_id`, `verdict`, `issues`, `terminal_state`, `failure_code`, `latency_ms`. |
| `run_metadata.subagent_observability_lane` | `fork_v3_enhanced` vs `legacy_routing_sse_only` — documents whether v3 lifecycle extras were active for this turn. |
| SSE `subagent_started` / `subagent_progress` / `subagent_finished` | Same `type` values as v1; **optional** extra keys when present: `parent_turn_id`, `spawn_reason`, `terminal_state` (on `subagent_finished` when known). |

**Train T3 lifecycle (v3, implemented 2026-05-07):** `<task-notification>` user-role transcript rows (LangGraph `HumanMessage` with `additional_kwargs.kind="task_notification"`), SSE mirror `subagent_task_notification`, throttled deterministic `subagent_progress_label`, and `subagent_heartbeat` while a routing leg is active (Settings-gated).

**Stubbed / next wave:** real coordinator-mode runtime, hooks (`SubagentStartHooks`) beyond existing hook chain, per-child token accounting beyond whole-turn `usage`, LLM-generated AgentSummary-style progress labels.

**Train T2 / Epic B (2026-05-07):** `specialist_results_v3` merge + optional `claim_verification` subagent when `SCIENCE_GRAPHRAG_AGENT_CLAIM_VERIFICATION_ENABLED=1` (see Settings); explicit spawn rows merge into `run_metadata.subagent_runs` alongside routing legs.

**Product architecture (where this spec sits):** research chat stays on the **simplified** single LangGraph run (supervisor → retrieval / graph → writer). Roadmap for goals, deferred work, and future **`tool_search`** plus **context-window summarization / compaction**: [`docs/analysis/agent-runtime-tools-context-roadmap-2026-05-04.md`](../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md). **Каталог инструментов (имена, схемы, карта кода):** [`docs/architecture/agent-chat-tools.md`](../architecture/agent-chat-tools.md). In this document, **CH\*** labels denote **delivery waves / features**, not separate shipped microservices.

## Client contract (what to read where)

- **Always prefer top-level envelope** for trust and UX: `answer_class`, `evidence_summary`, `warnings`, `thread_id`, `session_summary_excerpt`, `phoenix_trace_id`, `tool_trace`, typed blocks `inventory`, `quote_candidates`, `bibliography`, `relation_trace`, `idea_suggestions`.
- **`bibliography` object** may include `format`, `entries`, `filtered_work_ids`, and tool-local `warnings` (e.g. `some_work_ids_filtered`). Servers **also** surface bibliography filter signals in top-level `warnings` when applicable so clients that only read `warnings` still see them.
- **SSE stream extras** (`context_compacted`, `tool_search_result`, mid-run `warning`, etc.) are optional UX; the authoritative answer payload is **`final_answer`** (same shape as sync JSON). **JSON parity:** when `thread_id` is set, sync JSON includes `session_summary_excerpt` (post-turn server memory excerpt), matching the excerpt carried on SSE `context_compacted` / `final_answer`.

### UI traceability (product, 2026-04-27)

- **Chunk inspection** for trust / QA is the standalone route **`/evidence`** with query params `work_id`, optional `workspace_id`, and trace fields (`chunk_fingerprint`, `section`, `citation`). The React helper is **`buildStandaloneEvidencePath`** in `ui/src/components/work/traceabilityState.js`.
- **Do not** treat `?tab=evidence` on `/workspace` as a live workspace-shell mode; workspace shell is a paper list; chat-first evidence lives in **`AskAnswerPanel`** (citations, `evidence_summary`, typed blocks, **Inspect run**).

### `history_digest` parsing

- Accepted shapes: **JSON array of objects** as a **list** in the JSON body, or the same array **serialized as a JSON string** in the body.
- Non-dict elements inside the array are **dropped**; an empty array after filtering is **not** an error.
- If a **non-empty** string is sent and **JSON parsing fails**, or JSON parses to a **non-array** (e.g. object/scalar), the digest is **ignored** and the server adds top-level `warnings` entry **`history_digest_invalid`**. For SSE, a stream event `{"type":"warning","code":"history_digest_invalid",...}` is emitted after `intent_classified`, and the same code appears in `final_answer.warnings`.

## Request (`AgentQueryRequestV2`)

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `question` | string | yes | User message |
| `workspace_id` | string \| null | no | Workspace scope for tools |
| `max_tool_calls` | int \| null | no | 1–30; server default if omitted |
| `thread_id` | string \| null | no | **CH4:** stable id for server-side session memory (`memory` = process-local dict, `redis` = shared store when configured); client may use chat session id |
| `history_digest` | string \| list \| null | no | **CH4:** JSON **array** of turn objects, or that array as a JSON string; see §`history_digest` parsing |
| `answer_class_hint` | string \| null | no | Optional hint for routing/UI; does not force model behavior |

## Response envelope (`AgentQueryResponseV2`)

All new fields are **optional** for backward compatibility; clients should treat missing fields as null/empty.

| Field | Type | Notes |
|-------|------|--------|
| `answer` | string | Final assistant text |
| `citations` | array | Citation objects |
| `tool_trace` | array | `ToolCallTrace`-shaped dicts (includes synthetic `route_to_specialist` from supervisor) |
| `duration_ms` | int | |
| `phoenix_trace_id` | string \| null | OpenTelemetry trace id (hex) when a span is active |
| `thread_id` | string \| null | Echo of request `thread_id` when set |
| `session_summary_excerpt` | string \| null | **CH4:** First ≤500 chars of server `session_summary` after this turn when `thread_id` set; aligns with SSE `context_compacted.session_summary_excerpt` |
| `run_metadata` | object | Runtime flags, model ids, **`agent_runtime`** (graph selector; ADR-027), **`run_kind`** (`single_agent_research` \| `supervisor_specialists` \| **`supervisor_specialists_v3`**), **`graph_id`** (`single_agent_react` \| `supervisor_graph` \| **`supervisor_graph_v3`**), etc.; when `thread_id` is set, may include **`compaction`** (CH5 v1: `kind`, `kinds`, `trigger`, `digest_count`, `boundary`) and **`session_digest_count`** |
| `answer_class` | string | One of `inventory`, `fact_lookup`, `grounded_explanation`, `relation_tracing`, `quote_extraction`, `ideation`, `bibliography_export`, `synthesis` |
| `evidence_summary` | string \| null | Short human-readable evidence summary |
| `warnings` | array of string | e.g. `weak_evidence`, `no_workspace`, `graph_only`, `text_only`, `no_quote_found`, `no_quote_found_after_idea_hits`, `history_digest_invalid`, `agent_turn_deadline_exceeded`, `agent_partial_graph_recursion_limit`, `partial_after_recursion_limit`, `answer_salvaged_from_graph_tool`, `agent_finished_without_final_answer_tool` (tools were used and the model returned text, but the last executed catalog tool was not `final_answer` — suppressed when `answer_salvaged_from_graph_tool` is present; `tool_trace` stays honest; use for monitoring/UI) |
| `inventory` | object \| null | Papers/authors/counts when applicable |
| `relation_trace` | object \| null | Reserved / sparse in Wave A |
| `quote_candidates` | array \| null | Quote snippets + work/chunk ids |
| `idea_suggestions` | array \| null | Reserved for CH7 |
| `bibliography` | object \| null | `{ "format": "gost", "entries": [...] }`; may include `filtered_work_ids` and in-object `warnings` |

### Evidence-mix warnings (`graph_only` / `text_only`)

**Product decision (2026-04-28):** these codes stay **only** in the top-level `warnings` array. They are **not** duplicated into `product_markers` (`answered_with_tools`, `answered_directly`, …). Rationale: they describe retrieval **shape** for operators and analytics, not completion of a product journey; keeping a single source avoids drift between `warnings` and markers.

- **`graph_only`:** After stripping session/routing tools, the turn’s catalog tools include Neo4j graph tools (`cypher_query`, `edge_search`) and **no** vector-ish tools (`idea_search`, `paper_quote_search`). Does **not** imply failure; pair with `answer_class` / `tool_trace` for context (e.g. graph-heavy questions).
- **`text_only`:** Dual pattern for `relation_tracing` when vector tools ran but no graph tools — similarly informational.

Implementation: `science_graphrag/agent/chat_envelope.py` (`_append_evidence_warnings`).

## SSE event vocabulary v1

Each SSE `data:` line is a JSON object with a `type` field.

| `type` | When | Payload |
|--------|------|---------|
| `intent_classified` | Start of run | `answer_class`, `source` (e.g. `coordinator_gate_v0` for deterministic rules, `coordinator_gate_llm` / `coordinator_gate_fallback` for hybrid/LLM paths), `conversation_intent`, `tool_policy`, `route_hint`, `reason`, `confidence` (0–1), `classifier` (`deterministic` \| `llm` \| `fallback`), `suggested_answer_class` |
| `specialist_selected` | After supervisor routing | `from`, `to`, optional `budget_left`, optional `reason`, optional runtime attribution (`run_kind`, `graph_id`) |
| `subagent_started` | Immediately after `specialist_selected` | `subagent_id` (typically specialist id), optional `from`, optional `summary` (short, product-safe), optional **`parent_turn_id`**, **`spawn_reason`** (Train T3 B1) |
| `subagent_progress` | Optional, after `tool_call` while a subagent is active | `subagent_id`, `step`, `tool`, `summary`, optional **`parent_turn_id`**, **`spawn_reason`** |
| `subagent_finished` | When leaving a subagent (next routing or synthesis) | `subagent_id`, optional **`parent_turn_id`**, **`spawn_reason`**, **`terminal_state`**, **`latency_ms`** |
| `subagent_task_notification` | After a routing leg completes (v3) | Structured payload + `xml_excerpt` (same keys as `run_metadata.subagent_task_notifications[]`). |
| `claim_verification_result` | After each claim verification child completes (v3 + flag) | Same keys as `run_metadata.claim_verification_results[]` entries (`type` = `claim_verification_result`). |
| `subagent_heartbeat` | While awaiting graph chunks with an active routing leg (v3) | `subagent_id`, `parent_turn_id`, `reason` (`idle_tick`). |
| `subagent_progress_label` | Throttled UX label on new tool progress (v3) | `subagent_id`, `parent_turn_id`, `label`, `tool`, `step`. |
| `tool_search_result` | After rule shortlist (CH3) + Epic C0 discovery + optional LLM rerank (C1) | `specialist`, `tools`, `reason` (`rules` \| `hybrid_llm` \| `low_signal` \| …), `skipped`, optional `message_discovery_tools`, `message_discovery_merged` (LangGraph history), optional `carryover_tools`; Train T1 strict deferred: `activation_policy`, `rules_matched_tools`, `tool_search_miss_due_to_no_discovery`, `deferred_tool_activation_rate`, optional `deferred_strict_*` diagnostics; **Train T2 C1 hybrid:** optional `selector_stage`, `selector_confidence` (0–1), `selector_reason_codes` (string[]), `rules_candidate_tools`, `llm_ranked_tools`, `pre_llm_denied_tools` — clients may ignore unknown keys |
| `web_fetched` | After `web_fetch` tool returns (debug → SSE when streamable) | From tool payload `sse_hint`: bounded URL/host summary fields (product-safe); gated by `SCIENCE_GRAPHRAG_AGENT_WEB_RESEARCH_TOOLS_ENABLED` |
| `doi_resolved` | After `doi_resolver` tool returns (debug → SSE when streamable) | From tool payload `sse_hint`: normalized DOI, OpenAlex/workspace attribution; gated by `SCIENCE_GRAPHRAG_AGENT_DOI_RESOLVER_TOOL_ENABLED` |
| `mcp_audit` | After MCP surface tools (`call_mcp_tool` / `list_mcp_resources` / `fetch_mcp_resource` / `mcp_auth`) | `sse_hint` passthrough: `phase`, `server`, optional `tool` / `resource_uri`, `auth_status`, `ok`, optional `deny_reason`; gated by `SCIENCE_GRAPHRAG_AGENT_MCP_TOOLS_ENABLED` + `agent_mcp_http_base_url` for live RPC |
| `lsp_audit` | After bounded `lsp_tool` | `operation`, payload budget / timeout / `degraded` markers; gated by `SCIENCE_GRAPHRAG_AGENT_LSP_TOOL_ENABLED` |
| `runtime_monitor` | After `runtime_monitor_get` | `task_id`, `state`, optional `degraded`; gated by `SCIENCE_GRAPHRAG_AGENT_RUNTIME_MONITOR_TOOL_ENABLED` |
| `research_plan_updated` | After `research_plan_write` | `item_count`, `updated_at`; gated by `SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_TOOL_ENABLED` |
| `user_question_asked` | After `ask_user_question` | `request_id`, `question_count`; gated by `SCIENCE_GRAPHRAG_AGENT_ASK_USER_QUESTION_TOOL_ENABLED` |
| `user_answered` | Initial debug when client sends `user_structured_answer` matching pending ask | `request_id`, `answer_count`; requires `thread_id` + prior pending envelope |
| `brief_recorded` | After `brief` tool | `chars`; `run_metadata.brief` also set on `final_answer` when `SCIENCE_GRAPHRAG_AGENT_BRIEF_OUTPUT_ENABLED` |
| `tool_call` | LLM tool call | `step`, `tool`, `args_summary` |
| `tool_result` | Tool return | `step`, `tool`, `row_count`, `error` |
| `answer_synthesis_started` | After graph streaming completes, before `evidence_ready` / compaction | empty payload beyond `type` |
| `evidence_ready` | Before final | `citation_count` |
| `answer_synthesis_finished` | Immediately before `final_answer` | empty payload beyond `type` |
| `context_compacted` | After turn digest update (CH4) when `thread_id` is set | `thread_id`, `session_summary_excerpt`, **`compaction`**: `{ "kind": "turn_digest", "kinds": string[], "trigger": "post_answer" \| "post_answer_degraded_stream", "digest_count": int, "boundary": { "status": "idle" \| "candidate", ... } }` — `kinds` may include `rolling_memory` (after enough digests) and `workspace_capsule` when a workspace-scoped capsule exists; `post_answer_degraded_stream` when the graph stream did not yield a final `values` chunk; **`audit`** (eval CH5): `{ schema_version, digest_cap, rolling_threshold, workspace_capsule_present, llm_full_history_compact }` — reproducibility slice for compaction gates (`llm_full_history_compact` reserved for future L4 LLM-wide summarization) |

### Prompt / memory matrix after compaction (L1–L4)

Canonical ladder lives in [`docs/analysis/agent-runtime-tools-context-roadmap-2026-05-04.md`](../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md) §3. Below: **what can influence the model prompt** after server-side compaction on a turn (exact templating in `science_graphrag/agent/context/`).

| Layer | Source | Typically injected when |
|-------|--------|------------------------|
| L1 turn digest | `turn_digest` → thread store | Next turn via `history_digest` client echo + server merge (`apply_turn_digest_to_thread`) |
| L2 rolling session summary | `session_backend` rolling window over digests | `format_user_with_memory` / initial state builder when `thread_id` present |
| L3 workspace capsule | Session `capsules` / workspace scope | When workspace-bound thread has capsule materialization enabled; also reflected in `context_compacted.compaction.kinds` |
| L4 LLM consolidation | `SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED` (+ cooldown / token caps in Settings) | When digest window is full, optional chat-LLM rewrite of ``session_summary`` (cooldown-gated); **`audit.llm_full_history_compact`** + **`audit.llm_compact`** on SSE ``context_compacted``; sync JSON mirrors audit under ``run_metadata.compaction_audit`` |
| L4 boundary | `context_compacted.compaction.boundary` | Signals ``digest_window_full``; pairs with optional LLM consolidation above |
| Discovered tools carry-over | `capsules.discovered_tools` | Merged from prior turn digest tools; injected as `<discovered_tools>` block when flag enabled |
| Tool-message compact | `tool_message_compact` (ReAct) | Same-turn LangGraph messages only; independent of CH5 SSE compaction |
| Thread insight (Epic A, Train T1+) | `session_meta.thread_insight` | Optional long-thread synthesis snapshot; when `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=1`, refreshed after each turn with enough digests; audit mirrored under `run_metadata.thread_insight_audit` and control skips under `run_metadata.thread_insight_control` (sync + SSE). **Train T2 / A2:** first user message may include `<last_turn_digest>` then `<thread_insight status="fresh or conflicted">` then `<session_memory>`; coarse telemetry in `run_metadata` (`insight_fallback_reason`, `insight_conflict_resolved`, `ptl_retry_count`, …). |
| LangGraph message tool discovery (Epic C0) | `tool_search` metadata | Tool names from prior `AIMessage.tool_calls` / `ToolMessage` rows merge into the rule shortlist before session carry-over; see `tool_search_result.message_discovery_*` fields. |
| Away recap | `<away_recap>` | When client sends `client_idle_ms` above threshold (`agent_away_summary_*`) |
| `product_step` | Whenever the agent crosses a user-visible boundary (start of turn, hand-off, before synthesis, after compaction, on each non-meta `tool_call`) | `code` (e.g. `interpreting_question`, `delegating_to_<specialist>`, `composing_answer`, `updating_session_memory`, `searching_literature`, `using_tool`), optional `tool`, optional `specialist`; for fallback `using_tool` events also emit explicit generic marker fields (`generic=true`, `generic_reason`) |
| `agent_note` | **Optional** (off by default; gated by `agent_note_enabled`); short LLM-generated phrase emitted ≤ `agent_note_max_per_turn` times per turn after `intent_classified`, after each `specialist_selected`, and once per specialist's first `tool_result` | `kind` (`intent` \| `route` \| `tool`), `note` (≤200 chars plain prose). Costs extra LLM tokens; safe to ignore client-side |
| `final_answer` | End | Full envelope fields + legacy `answer`, `citations`, `tool_trace` (includes `session_summary_excerpt` when `thread_id` set) |
| `warning` | Any time | `code`, `message` (optional `reason` / `confidence` for coordinator fallback) |
| `error` | Fatal | `detail`, `code` (legacy: `agent_runtime_error`, `agent_turn_deadline_exceeded`, `agent_graph_recursion_limit`), optional `error_class` (stable enum the UI localizes via `chat.errors.<error_class>`: `provider_unauthorized`, `provider_forbidden`, `provider_rejected`, `provider_timeout`, `provider_unreachable`, `agent_turn_deadline_exceeded`, `agent_recursion_limit`, `llm_output_validation_error`, `llm_output_parse_error`, `internal_error`), optional safe English `message`. Recursion-limit error events also carry the numeric `recursion_limit`. |

### Summarization modes (Epic A — spec first)

Roadmap: [`docs/analysis/agent-runtime-tools-context-roadmap-2026-05-04.md`](../analysis/agent-runtime-tools-context-roadmap-2026-05-04.md) §9.3. Three **modes** describe how rolling memory coexists with long-thread insight (implementation is feature-flagged per mode).

| Mode | Purpose | Primary inputs | Artifact | Injected into prompt (when enabled) | Stale / invalidation (target) |
|------|---------|----------------|----------|-------------------------------------|--------------------------------|
| `turn_loop_memory` | Default CH4/CH5 continuity | Turn digests, rolling `session_summary`, optional L4 LLM compact | `session_summary`, `context_compacted`, capsules | `<session_memory>`, `<workspace_capsule>`, `<discovered_tools>` via `format_user_with_memory` | Rolling window cap; L4 cooldown + digest boundary |
| `thread_insights_compact` | Long-thread recall / consistency | Full digest window (server), chunked workers | `session_meta.thread_insight` (`current`, `version`, `sources`, `compaction_boundary`, `audit`) | **A2:** `<thread_insight>` + `<last_turn_digest>` in first user message when policy allows | **A1:** TTL (`agent_thread_insights_ttl_seconds`, 0=off) + `agent_thread_insights_stale_after_turn_delta` + high-churn (`agent_thread_insights_high_churn_*`); audit `stale_reason` (`turn_delta` \| `ttl` \| `high_churn` \| `manual`); `run_metadata.thread_insight_control` for `refresh_decision` / skips; circuit-breaker in `session_meta.insight_circuit` |
| `hybrid` | Turn-loop + periodic insight refresh | Same as both | Both artifacts | Ordered merge with explicit **precedence** (A2): `turn_digest` (latest facts) > fresh `thread_insight` > `session_summary` | Union of both policies; never silent override of fresher turn facts |

**Negative / edge cases (must stay defined in tests + trace):**

- Empty or single-turn thread: no `thread_insight` snapshot (below `agent_thread_insights_min_digests`).
- Contradicting summaries vs last user/tool facts: **fresh turn digest / tool results win**; conflicting insight claims marked `conflicted` until refresh (**A2**).
- Insight generation failure / timeout: fall back to `session_summary` only; `insight_fallback_reason` in metadata (**A2**).
- Tool loop churn: forces refresh with `stale_reason=high_churn` when over threshold; repeated build failures open circuit-breaker (skip refresh for N turns) — **A1** runtime; prompt-side fallback labels remain **A2**.

**Train T1 note:** runtime ships **deterministic stub** chunk summaries + parallel workers + `thread_insight_audit_v1`; optional LLM synthesis via forked runtime when enabled.

**Train T1+ / A1 hardening note:** orchestration above (freshness, control plane, `compaction_boundary` v1, locks, L4 PTL retry, message-group integrity helpers) is implemented.

**Train T2 / A2 note:** prompt precedence and `<thread_insight>` / `<last_turn_digest>` injection are implemented in `resolve_prompt_memory_policy` + `format_user_with_memory` (see roadmap §9.3 A2).

### UI vocabulary contract

These string identifiers travel as raw codes over the wire and are **internal**:
the UI must localize them rather than render them verbatim. Source of truth on
the frontend is [`ui/src/components/work/agent/agentRunVocabulary.js`](../../ui/src/components/work/agent/agentRunVocabulary.js)
which exposes `mapSpecialistToLabel`, `mapAnswerClassToLabel`,
`mapToolSearchReasonToLabel`, `mapRouteReasonToLabel`, `mapIntentSourceToLabel`,
and `mapErrorCodeToLabel`. Unknown codes flow through `humanizeUnknownCode` so
unmapped values still render readably.

**Live card (Ask):** the primary headline never uses `tool_search_result` (internal
shortlist plumbing). The expandable «recent lines» strip omits `tool_search_result`
and each `tool_result` row so users see intent / routing / `product_step` / `tool_call`
lines without repeating «N rows» spam; full steps remain in specialist run groups /
run inspector.

**Decision / Why block:** above the headline the live card surfaces a two-line
«Решение / Почему» (`Decision: <answer_class>` and `Why: <reason>`) derived from
the latest `intent_classified` (or, when the intent had no `reason`, from the
most recent `specialist_selected.reason`). The «Why» line is hidden when the
reason is the redundant default `single_agent_research_runtime`. When
`agent_note_enabled=true` and the run is rendered in `chat detailLevel=detailed`,
the most recent `agent_note.note` text appears as a third italic line in this
block.

**Repeated steps:** the live card and specialist run stack collapse adjacent
repeats of the same `tool_call` / `product_step` into a single line with a
suffix from `chat.run.headline.repeatedSuffix` (`{{base}} (×{{count}})`). The
group key is `tool_call:<tool>` or `product_step:<code>` (with the tool name
appended for `using_tool`).

| Field | Code domain |
|-------|-------------|
| `answer_class` | `inventory`, `fact_lookup`, `grounded_explanation`, `relation_tracing`, `quote_extraction`, `ideation`, `bibliography_export`, `synthesis` |
| `tool_search_result.specialist` / `specialist_selected.from` / `.to` | `supervisor`, `retrieval_agent`, `graph_agent`, `writer_agent`, `single_agent_react` |
| `tool_search_result.reason` | `rules`, `hybrid_llm`, `low_signal`, `fallback_full`, `fallback_full_single_agent`, `disabled`, `writer_minimal_set` |
| `intent_classified.source` | `single_agent_research_v1`, `coordinator_gate_v0`, `coordinator_gate_<classifier>`, `heuristic`, `deterministic`, `shortcut` |
| `specialist_selected.reason` (and `subagent_started.summary` when sourced from routing log) | `single_agent_research_runtime`, `coordinator_route_hint`, `semantic_fast_route`, `supervisor_round_cap`, `budget_exhausted`, `coordinator_classifier_fallback` |
| `product_step.code` | `interpreting_question`, `delegating_to_retrieval_agent`, `delegating_to_graph_agent`, `delegating_to_writer_agent`, `delegating_to_single_agent_react`, `delegating_to_supervisor`, `delegating_to_specialist`, `composing_answer`, `updating_session_memory`, plus tool-derived codes from `product_step_code_for_tool` (`searching_literature`, `browsing_ideas`, `gathering_evidence`, `summarizing_workspace`, `exploring_graph`, `paper_lookup`, `paper_metadata`, `finding_quotes`, `formatting_bibliography`, `final_answer`) and the catch-all `using_tool` |
| `agent_note.kind` | `intent`, `route`, `tool` (UI shows latest note as auxiliary; never part of final answer) |
| `error.error_class` | `provider_unauthorized`, `provider_forbidden`, `provider_rejected`, `provider_timeout`, `provider_unreachable`, `agent_turn_deadline_exceeded`, `agent_recursion_limit`, `llm_output_validation_error`, `llm_output_parse_error`, `internal_error` |

Raw values still appear unchanged in `tool_trace`, `routing_log`, `debug_events`
and Phoenix spans (consumed by inspectors and eval pipelines).

## Recursion-limit handling

The LangGraph agent has two structural caps that can stop a turn early. Both are
addressed end-to-end (graph → API/SSE → UI).

1. **Soft-cap inside ReAct (preventive).** `react_after_tools_decrement_budget`
   tracks `react_total_hops`, `react_consecutive_same_batch_count`, and repeated
   `paper_profile.work_id`. When any threshold is crossed
   (`agent_react_max_consecutive_same_batch`, `agent_react_max_total_hops`, or
   the second consecutive same `work_id`), it sets
   `metadata.react_force_finalize = "<reason>"`. The next `route_react_chat_to_tools`
   re-routes any non-`final_answer` batch to `final_answer_nudge`, and
   `route_react_tools_next` returns `END` once the forced batch finishes — so
   the run closes well before the hard limit.
2. **Hard recursion limit (LangGraph).** `agent_supervisor_recursion_limit`
   (default 64; validated at startup against `4 * agent_max_tool_calls + 8`)
   counts every node transition. If LangGraph still raises
   `GraphRecursionError`, both `invoke_graph_with_deadline` and
   `iter_graph_chunks` wrap it into the domain
   `AgentGraphRecursionLimitExceeded`. The SSE handler then mirrors the deadline
   recovery flow:
   - if `latest_full_state` has a salvageable assistant draft, the stream emits
     `warning { code: "agent_partial_graph_recursion_limit", recursion_limit }`
     followed by a normal `final_answer` whose `run_metadata` contains
     `salvaged_after_recursion_limit: true`, `recursion_limit`, and (when
     available) `react_total_hops` / `react_force_finalize`. The envelope adds
     `agent_partial_graph_recursion_limit` and `partial_after_recursion_limit`
     to `warnings`/`product_markers`;
   - otherwise the stream emits a structured
     `error { code: "agent_graph_recursion_limit", error_class: "agent_recursion_limit", recursion_limit }`
     with no LangChain URL or raw message. The sync JSON path returns an
     `AgentQueryResponseV2` carrying the same warning and
     `run_metadata.agent_graph_recursion_limit_exceeded = true`.

**Observability.** Phoenix span events:
`agent.react_force_finalize` (soft-cap engaged, with `reason` and counters),
`agent.graph_recursion_limit_hit` (hard limit fired, with `recursion_limit` and
`salvage_state_present`).

**UX.** UI localizes `chat.errors.agent_recursion_limit` and
`chat.warnings.agent_partial_graph_recursion_limit` (en/ru); the existing
warning chip layer in `AskAnswerPanel` surfaces the partial-after-limit hint
without a new component.

## Compatibility

- Unknown `type` values: clients must ignore forward-compatibly.
- `final_answer` must remain parseable by legacy UI (at minimum `answer`, `citations`, `tool_trace`).

## Operations

- Runbook: [`docs/runbooks/agent-chat-v2.md`](../runbooks/agent-chat-v2.md) (SSE/proxy, Redis sessions, timeouts, release gate).

## Related code

- API: `science_graphrag/api/agent_v2.py`
- Envelope: `science_graphrag/agent/chat_envelope.py`
- Stream/trace parity: `science_graphrag/agent/graph/tracing.py` + `collect_tool_trace`
- Tools: `science_graphrag/agent/tools/*`, manifest: `science_graphrag/agent/tool_manifest.py`, search: `science_graphrag/agent/tool_search.py`
