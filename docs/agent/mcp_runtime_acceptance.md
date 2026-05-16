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

`tests/agent/test_product_surfaces.py::test_native_external_tools_independent_of_mcp_unconfigured` asserts native `web_search` registers while MCP returns `mcp_unconfigured` when the adapter URL is unset.

## Settings / operator surface (Phase 6)

- Snapshot: `agent_tools.integrations` exposes `mcp_operator_state` (`disabled` | `unconfigured` | `configured`), effective timeout, denylist preview, adapter host (hostname only), and `mcp_auth_model=delegation_required`.
- Persisted PATCH (allowlist): `agent_mcp_request_timeout_seconds`, `agent_mcp_server_denylist`, `agent_mcp_http_base_url` (empty string clears persisted override and falls back to env).
- Operator source tests: `POST /v1/settings/agent_tools/test_source` with `source_id="mcp"` stores `last_test` / `last_error` diagnostics in snapshot.
- Optional operator smoke: `scripts/live_check/mcp_adapter_smoke.py` (JSON-RPC `tools/list` against configured base URL).

## Operator acceptance checklist

Run from repo root with project venv.

1. **Snapshot exposes MCP operator fields**
   - Command:
     - `.venv/bin/pytest tests/test_settings_service.py::test_update_agent_tools_settings_persists_mcp_knobs -q`
   - Expected:
     - `1 passed`
     - Snapshot `agent_tools.integrations` includes `mcp_operator_state`, `mcp_request_timeout_seconds`, `mcp_server_denylist_count`, `mcp_server_denylist_preview`, `mcp_auth_model`.

2. **Runtime overlay applies persisted MCP knobs**
   - Command:
     - `.venv/bin/pytest tests/test_runtime_overlay.py::test_build_non_secret_overrides_merges_mcp_knobs -q`
   - Expected:
     - `1 passed`
     - Overlay contains normalized `agent_mcp_server_denylist` and bounded `agent_mcp_request_timeout_seconds`.

3. **Native external tools remain independent when MCP is unconfigured**
   - Command:
     - `.venv/bin/pytest tests/agent/test_product_surfaces.py::test_native_external_tools_independent_of_mcp_unconfigured -q`
   - Expected:
     - `1 passed`
     - `web_search` still registers; MCP returns `mcp_unconfigured`.

4. **UI integratons card renders MCP states/advanced controls**
   - Command:
     - `cd ui && npm run test -- --run src/pages/SettingsPage/AgentToolsSettingsPanel.test.jsx`
   - Expected:
     - Vitest green for MCP state chip + advanced fields and MCP payload save assertions.

5. **Live adapter smoke (optional, operator lane)**
   - Preconditions:
     - MCP JSON-RPC adapter reachable from the API process (host stub on `0.0.0.0` or compose service).
     - `SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL` set for the API container (see `docker-compose.mcp-live-check.yml`).
   - Commands:
     - `.venv/bin/python scripts/live_check/mcp_jsonrpc_stub.py --host 0.0.0.0 --port 19999` (background)
     - `.venv/bin/python scripts/live_check/mcp_adapter_smoke.py --server smoke`
   - Expected:
     - `http_status=200`
     - `rpc_ok=1`
   - Failure contract:
     - Non-zero exit with `transport_error`, `json_error`, or `rpc_error`.

6. **Live agent E2E (optional, operator lane)**
   - Preconditions:
     - Stable API: `COMPOSE_FILE=docker-compose.dev.yml:docker-compose.live-check.yml:docker-compose.mcp-live-check.yml docker compose up -d api --force-recreate`
     - MCP stub listening on host port `19999` (`--host 0.0.0.0` so `host.docker.internal` works from Docker).
     - LLM reachable from API (OpenRouter or Ollama via `host.docker.internal:11434/v1`).
     - `export AGENT_LIVE_BASE=http://127.0.0.1:18787` and `AGENT_LIVE_WORKSPACE_ID=<workspace>`.
   - Command:
     - `.venv/bin/python scripts/live_check/mcp_agent_e2e_smoke.py --start-stub`
   - Expected:
     - `mcp_agent_e2e_ok=1`
     - `call_mcp_tool` in `tool_trace`
     - `run_metadata.mcp_audit_summary.last` with `phase=call`, `ok=true`

## Latest operator run evidence (2026-05-16)

### Adapter smoke (green)

- Stub: `scripts/live_check/mcp_jsonrpc_stub.py --host 0.0.0.0 --port 19999`
- Command: `SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL=http://127.0.0.1:19999/rpc .venv/bin/python scripts/live_check/mcp_adapter_smoke.py --server smoke`
- Observed: `http_status=200`, `rpc_ok=1`, exit `0`

### Agent E2E via `/v2/agent/query` (green)

- Contour: `make dev-up` + MCP live-check compose overlay; API `http://127.0.0.1:18787`; workspace `ws-pilot-od`; LLM patched to OpenRouter for container reachability.
- Command: `.venv/bin/python scripts/live_check/mcp_agent_e2e_smoke.py --skip-adapter-smoke`
- Observed:
  - `tool_trace_tools` includes `call_mcp_tool`
  - `mcp_audit_summary` with `event_count=1`, `last.phase=call`, `last.ok=true`
  - `mcp_agent_e2e_ok=1`, exit `0`

### Settings source-test endpoint (green)

- Command:
  - `PATCH /v1/settings/agent_tools {"agent_mcp_http_base_url":"http://host.docker.internal:19999/rpc"}`
  - `POST /v1/settings/agent_tools/test_source {"source_id":"mcp"}`
- Observed:
  - `200 OK`, payload includes `{"ok": true, "detail": "ok"}`
  - snapshot `agent_tools.integrations` reflects `mcp_adapter_url_source="settings"` and fresh diagnostics timestamp

### Prior lane (preflight guard)

- Command: `mcp_adapter_smoke.py` without `SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL`
- Observed: `missing_base_url`, exit `1` — expected guard when adapter URL unset.
