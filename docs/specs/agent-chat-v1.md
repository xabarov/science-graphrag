# Agent Chat API v1 (research workspace)

**Status:** implemented (Wave A — CH1+CH2+CH3)  
**HTTP:** `POST /v2/agent/query`  
**Modes:** JSON (`Accept: application/json`) or SSE (`Accept: text/event-stream`)

## Request (`AgentQueryRequestV2`)

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `question` | string | yes | User message |
| `workspace_id` | string \| null | no | Workspace scope for tools |
| `max_tool_calls` | int \| null | no | 1–30; server default if omitted |
| `thread_id` | string \| null | no | Reserved for CH4; accepted, ignored in Wave A |
| `history_digest` | string \| null | no | Reserved for CH4; accepted, ignored in Wave A |
| `answer_class_hint` | string \| null | no | Optional hint for routing/UI; does not force model behavior |

## Response envelope (`AgentQueryResponseV2`)

All new fields are **optional** for backward compatibility; clients should treat missing fields as null/empty.

| Field | Type | Notes |
|-------|------|--------|
| `answer` | string | Final assistant text |
| `citations` | array | Citation objects |
| `tool_trace` | array | `ToolCallTrace`-shaped dicts (includes synthetic `route_to_specialist` from supervisor) |
| `duration_ms` | int | |
| `phoenix_trace_id` | string \| null | |
| `run_metadata` | object | Runtime flags, model ids, etc. |
| `answer_class` | string | One of `inventory`, `fact_lookup`, `grounded_explanation`, `relation_tracing`, `quote_extraction`, `ideation`, `bibliography_export`, `synthesis` |
| `evidence_summary` | string \| null | Short human-readable evidence summary |
| `warnings` | array of string | e.g. `weak_evidence`, `no_workspace` |
| `inventory` | object \| null | Papers/authors/counts when applicable |
| `relation_trace` | object \| null | Reserved / sparse in Wave A |
| `quote_candidates` | array \| null | Quote snippets + work/chunk ids |
| `idea_suggestions` | array \| null | Reserved for CH7 |
| `bibliography` | object \| null | `{ "format": "gost", "entries": [...] }` |

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
| `context_compacted` | Reserved CH5 | — |
| `final_answer` | End | Full envelope fields + legacy `answer`, `citations`, `tool_trace` |
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
