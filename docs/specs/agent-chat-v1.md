# Agent Chat API v1 (research workspace)

**Status:** implemented — **Wave A** (CH1+CH2+CH3) + **Wave B** (CH4 v1 in-process session: `thread_id`, `history_digest`, turn digest, SSE `context_compacted`, `session_init` in `tool_trace`).  
**HTTP:** `POST /v2/agent/query`  
**Modes:** JSON (`Accept: application/json`) or SSE (`Accept: text/event-stream`)

## Client contract (what to read where)

- **Always prefer top-level envelope** for trust and UX: `answer_class`, `evidence_summary`, `warnings`, `thread_id`, `session_summary_excerpt`, `phoenix_trace_id`, `tool_trace`, typed blocks `inventory`, `quote_candidates`, `bibliography`, `relation_trace`, `idea_suggestions`.
- **`bibliography` object** may include `format`, `entries`, `filtered_work_ids`, and tool-local `warnings` (e.g. `some_work_ids_filtered`). Servers **also** surface bibliography filter signals in top-level `warnings` when applicable so clients that only read `warnings` still see them.
- **SSE stream extras** (`context_compacted`, `tool_search_result`, mid-run `warning`, etc.) are optional UX; the authoritative answer payload is **`final_answer`** (same shape as sync JSON). **JSON parity:** when `thread_id` is set, sync JSON includes `session_summary_excerpt` (post-turn server memory excerpt), matching the excerpt carried on SSE `context_compacted` / `final_answer`.

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
| `thread_id` | string \| null | no | **CH4:** stable id for server-side session memory (in-memory store); client may use chat session id |
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
| `run_metadata` | object | Runtime flags, model ids, etc. |
| `answer_class` | string | One of `inventory`, `fact_lookup`, `grounded_explanation`, `relation_tracing`, `quote_extraction`, `ideation`, `bibliography_export`, `synthesis` |
| `evidence_summary` | string \| null | Short human-readable evidence summary |
| `warnings` | array of string | e.g. `weak_evidence`, `no_workspace`, `history_digest_invalid` |
| `inventory` | object \| null | Papers/authors/counts when applicable |
| `relation_trace` | object \| null | Reserved / sparse in Wave A |
| `quote_candidates` | array \| null | Quote snippets + work/chunk ids |
| `idea_suggestions` | array \| null | Reserved for CH7 |
| `bibliography` | object \| null | `{ "format": "gost", "entries": [...] }`; may include `filtered_work_ids` and in-object `warnings` |

## SSE event vocabulary v1

Each SSE `data:` line is a JSON object with a `type` field.

| `type` | When | Payload |
|--------|------|---------|
| `intent_classified` | Start of run | `answer_class`, `source` (`heuristic` \| `hint`) |
| `specialist_selected` | After supervisor routing | `from`, `to`, optional `budget_left` |
| `tool_search_result` | After rule shortlist (CH3) | `specialist`, `tools`, `reason`, `skipped` |
| `tool_call` | LLM tool call | `step`, `tool`, `args_summary` |
| `tool_result` | Tool return | `step`, `tool`, `row_count`, `error` |
| `evidence_ready` | Before final | `citation_count` |
| `context_compacted` | After turn digest update (CH4) when `thread_id` is set | `thread_id`, `session_summary_excerpt`, optional **`compaction`** object: `{ "kind": "turn_digest", "trigger": "post_answer" \| "post_answer_degraded_stream" }` (CH5 foundation: `post_answer_degraded_stream` when the graph stream did not yield a final `values` chunk) |
| `final_answer` | End | Full envelope fields + legacy `answer`, `citations`, `tool_trace` (includes `session_summary_excerpt` when `thread_id` set) |
| `warning` | Any time | `code`, `message` |
| `error` | Fatal | `detail` |

## Compatibility

- Unknown `type` values: clients must ignore forward-compatibly.
- `final_answer` must remain parseable by legacy UI (at minimum `answer`, `citations`, `tool_trace`).

## Related code

- API: `science_graphrag/api/agent_v2.py`
- Envelope: `science_graphrag/agent/chat_envelope.py`
- Stream/trace parity: `science_graphrag/agent/graph/tracing.py` + `collect_tool_trace`
- Tools: `science_graphrag/agent/tools/*`, manifest: `science_graphrag/agent/tool_manifest.py`, search: `science_graphrag/agent/tool_search.py`
