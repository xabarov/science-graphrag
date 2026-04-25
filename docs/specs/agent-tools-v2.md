# Agent Tools API v2 - Specification

**Status:** Draft (Wave Y3, 2026-04-25)  
**Supersedes:** `docs/specs/agent-tools-v1.md` (v1 deprecated, not yet removed)

## Endpoint

```
POST /v2/agent/query
Content-Type: application/json
Accept: application/json          # -> sync JSON response
Accept: text/event-stream         # -> SSE stream
```

## Request

| Field            | Type           | Required | Default  | Notes                       |
|------------------|----------------|----------|----------|-----------------------------|
| `question`       | string (>=1 ch)| yes      | -        | Natural-language query      |
| `workspace_id`   | string \| null | no       | null     | Scopes retrieval            |
| `max_tool_calls` | int [1..30]    | no       | settings | Override agent budget       |

## SSE Event Stream (Accept: text/event-stream)

Events are emitted in chronological order. Each `data:` line is a JSON object.

| Event type     | When emitted                     | Key fields                                                                 |
|----------------|----------------------------------|----------------------------------------------------------------------------|
| `tool_call`    | Before tool execution            | `step`, `tool`, `args_summary`                                             |
| `tool_result`  | After tool execution             | `step`, `tool`, `row_count`, `error`                                       |
| `token`        | Each LLM output token (optional) | `delta` (string fragment)                                                  |
| `final_answer` | Graph END reached                | `answer`, `citations`, `tool_trace`, `duration_ms`, `phoenix_trace_id`, `run_metadata` |
| `error`        | Unhandled exception              | `detail` (string)                                                          |

Example stream:

```
data: {"type":"tool_call","step":1,"tool":"entity_search","args_summary":{"query":"BERT"}}

data: {"type":"tool_result","step":1,"tool":"entity_search","row_count":5,"error":null}

data: {"type":"final_answer","answer":"BERT is...","citations":[...],"tool_trace":[...],"duration_ms":1240,"phoenix_trace_id":"abc123","run_metadata":{...}}
```

## Sync JSON Response (Accept: application/json)

Identical to v1 `AgentQueryResponse`, plus `phoenix_trace_id` field:

```json
{
  "answer": "...",
  "citations": [...],
  "tool_trace": [...],
  "duration_ms": 1240,
  "phoenix_trace_id": "abc123",
  "run_metadata": {
    "agent_runtime": "langgraph_react_v1",
    "agent_enabled": true,
    "agent_max_tool_calls": 8
  }
}
```

## Deprecation of v1

`POST /v1/agent/query` remains available during transition with headers:

```
Deprecation: true
Sunset: 2026-07-01
Link: </v2/agent/query>; rel="successor-version"
```

## Error Responses

| Status | Condition                        |
|--------|----------------------------------|
| 503    | `agent_enabled=false` in config  |
| 422    | Validation error in request body |
| 500    | Unhandled exception              |
