# MCP runtime trio — acceptance notes

## Scope (this document)

Covers **`call_mcp_tool`**, **`list_mcp_resources`**, **`fetch_mcp_resource`** plus audit hints. **`mcp_auth`** remains a **delegation marker only** (no OAuth implementation); do not expand auth scope in routine acceptance work.

## Unconfigured vs deny vs success

| Path | Expected tool payload | SSE / debug (`mcp_audit`) |
|------|------------------------|---------------------------|
| Feature disabled | `error: "disabled"` | `phase=gate`, `ok=false` |
| Server on denylist | `error: "permission_denied"` | `phase=deny`, `deny_reason` set |
| Missing `agent_mcp_http_base_url` | `error: "mcp_unconfigured"` | `phase=unconfigured` |
| HTTP / parse failure | `error: mcp_transport_error` or `mcp_rpc_error` | `phase` matches tool, `ok=false` |
| Happy path | `ok: true` + `result` | `phase=call` / `list_resources` / `fetch_resource`, `ok=true` |

## Trace review / regression

- Raw `mcp_audit` rows appear in the agent SSE stream when streamable.
- Aggregated acceptance signal: **`run_metadata.mcp_audit_summary`** from `extract_runtime_telemetry_from_debug_events` (see `tests/agent/test_debug_events_telemetry.py`).
- Prefer summary + last event snapshot for diffing traces across releases.

## Minimal integration test

`tests/agent/test_product_surfaces.py::test_mcp_call_tool_json_rpc_ok` stubs `httpx.Client` and asserts JSON-RPC success + audit hint shape (no real MCP server required in CI).
