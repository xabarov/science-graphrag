# Agent tools v1 (Wave R)

## Scope

Read-only tool registry for retrieval agent benchmark family `agent_tools_v1`.

Tools:

1. `cypher_query(query, params={})`
2. `entity_search(kind, q, limit=10)`
3. `edge_search(node_id, rel_types=[], direction=both, limit=50)`
4. `idea_search(q, kinds=[chunk,work], workspace_id?, top_k=5)`
5. `summarize_workspace(workspace_id, top_n_works=8)`
6. `final_answer(answer, citations=[])`

## Safety

- `cypher_query` enforces read-only allowlist and rejects write tokens.
- max `LIMIT` is `200`.
- agent execution has `max_tool_calls` cap (default from settings: `8`).

## Endpoint contract

`POST /v1/agent/query`

Request:

```json
{
  "question": "string",
  "workspace_id": "optional-string",
  "max_tool_calls": 8
}
```

Response:

```json
{
  "answer": "string",
  "citations": [],
  "tool_trace": [],
  "duration_ms": 0,
  "run_metadata": {}
}
```
