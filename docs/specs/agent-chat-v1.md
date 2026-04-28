# Agent Chat API v1 (research workspace)

**Status:** implemented — **Wave A** (CH1+CH2+CH3) + **Wave B** (CH4 v1 session: `thread_id`, `history_digest`, turn digest, SSE `context_compacted`, `session_init` in `tool_trace`) + **Wave Next** (optional **Redis** session persistence via `SCIENCE_GRAPHRAG_AGENT_SESSION_MEMORY_BACKEND`, CH5 v1 compaction metadata, sync `run_metadata.compaction` parity).  
**HTTP:** `POST /v2/agent/query`  
**Modes:** JSON (`Accept: application/json`) or SSE (`Accept: text/event-stream`)

**Product architecture (where this spec sits):** research chat stays on the **simplified** single LangGraph run (supervisor → retrieval / graph → writer). Roadmap for goals, deferred work, and future **`tool_search`** plus **context-window summarization / compaction**: [`docs/analysis/chat-agent-system-roadmap-2026-04-26.md`](../analysis/chat-agent-system-roadmap-2026-04-26.md). **Каталог инструментов (имена, схемы, карта кода):** [`docs/architecture/agent-chat-tools.md`](../architecture/agent-chat-tools.md). In this document, **CH\*** labels denote **delivery waves / features**, not separate shipped microservices.

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
| `run_metadata` | object | Runtime flags, model ids, etc.; when `thread_id` is set, may include **`compaction`** (CH5 v1: `kind`, `kinds`, `trigger`, `digest_count`, `boundary`) and **`session_digest_count`** |
| `answer_class` | string | One of `inventory`, `fact_lookup`, `grounded_explanation`, `relation_tracing`, `quote_extraction`, `ideation`, `bibliography_export`, `synthesis` |
| `evidence_summary` | string \| null | Short human-readable evidence summary |
| `warnings` | array of string | e.g. `weak_evidence`, `no_workspace`, `graph_only`, `text_only`, `no_quote_found`, `no_quote_found_after_idea_hits`, `history_digest_invalid`, `agent_turn_deadline_exceeded`, `answer_salvaged_from_graph_tool`, `agent_finished_without_final_answer_tool` (tools were used and the model returned text, but the last executed catalog tool was not `final_answer` — suppressed when `answer_salvaged_from_graph_tool` is present; `tool_trace` stays honest; use for monitoring/UI) |
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
| `specialist_selected` | After supervisor routing | `from`, `to`, optional `budget_left`, optional `reason` |
| `subagent_started` | Immediately after `specialist_selected` | `subagent_id` (typically specialist id), optional `from`, optional `summary` (short, product-safe) |
| `subagent_progress` | Optional, after `tool_call` while a subagent is active | `subagent_id`, `step`, `tool`, `summary` |
| `subagent_finished` | When leaving a subagent (next routing or synthesis) | `subagent_id` |
| `tool_search_result` | After rule shortlist (CH3) | `specialist`, `tools`, `reason`, `skipped` |
| `tool_call` | LLM tool call | `step`, `tool`, `args_summary` |
| `tool_result` | Tool return | `step`, `tool`, `row_count`, `error` |
| `answer_synthesis_started` | After graph streaming completes, before `evidence_ready` / compaction | empty payload beyond `type` |
| `evidence_ready` | Before final | `citation_count` |
| `answer_synthesis_finished` | Immediately before `final_answer` | empty payload beyond `type` |
| `context_compacted` | After turn digest update (CH4) when `thread_id` is set | `thread_id`, `session_summary_excerpt`, **`compaction`**: `{ "kind": "turn_digest", "kinds": string[], "trigger": "post_answer" \| "post_answer_degraded_stream", "digest_count": int, "boundary": { "status": "idle" \| "candidate", ... } }` — `kinds` may include `rolling_memory` (after enough digests) and `workspace_capsule` when a workspace-scoped capsule exists; `post_answer_degraded_stream` when the graph stream did not yield a final `values` chunk |
| `final_answer` | End | Full envelope fields + legacy `answer`, `citations`, `tool_trace` (includes `session_summary_excerpt` when `thread_id` set) |
| `warning` | Any time | `code`, `message` (optional `reason` / `confidence` for coordinator fallback) |
| `error` | Fatal | `detail`, optional `code` (e.g. `agent_runtime_error`, `agent_turn_deadline_exceeded`) |

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
