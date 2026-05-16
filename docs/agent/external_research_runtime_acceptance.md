# External research runtime acceptance

## Purpose

Single entrypoint for operator acceptance checks across external research surfaces.
Use this index to pick the correct checklist for the component you are validating.

## Acceptance map

1. **MCP runtime surface**
   - Scope: `call_mcp_tool`, `list_mcp_resources`, `fetch_mcp_resource`, `mcp_auth` delegation marker.
   - Checklist: `docs/agent/mcp_runtime_acceptance.md` → **Operator acceptance checklist**.
   - Includes: snapshot/operator-state checks, PATCH overlay checks, isolation check, optional MCP adapter smoke.

2. **Semantic Scholar (Phase 5A)**
   - Scope: `semantic_scholar_search`, `semantic_scholar_paper`.
   - Checklist: `docs/agent/semantic_scholar_runtime_acceptance.md` → **Operator acceptance checklist**.
   - Includes: unit contract, registry toggle checks, optional live smoke and failure contract.

3. **PDF read pipeline live matrix (Phase 4)**
   - Scope: external PDF read/extract operator lane validation.
   - Checklist: `scripts/live_check/pdf_read_live_matrix.md`.
   - Includes: happy-path/blocked-path matrix and operator evidence expectations.

## Recommended execution order

1. Run MCP runtime checklist (surface health + policy contract).
2. Run Semantic Scholar checklist (metadata search/paper lookup health).
3. Run PDF live matrix (heavier extraction path).

This order keeps low-latency metadata checks ahead of long-running PDF validation.

## Evidence policy

- Keep acceptance evidence in operator artifacts for the current release lane.
- If a source remains unverified in live lane, keep its status as `needs_live_smoke`.
- Do not treat optional live smoke as default CI; run in operator lanes only.

## Latest lane snapshot (2026-05-16)

- **MCP adapter smoke:** green (`http_status=200`, `rpc_ok=1`) with host stub `mcp_jsonrpc_stub.py` on port `19999` and `docker-compose.mcp-live-check.yml` API overlay.
- **MCP agent E2E:** green (`mcp_agent_e2e_ok=1`, `call_mcp_tool` in `tool_trace`, `mcp_audit_summary.last.ok=true`) via `scripts/live_check/mcp_agent_e2e_smoke.py` against `AGENT_LIVE_BASE=http://127.0.0.1:18787`.
- **Semantic Scholar smoke:** observed `429 Too Many Requests` (failure contract validated; source remains `needs_live_smoke` until green run with valid key/quota window).
- **OpenAlex smoke:** green (`http_status=200`, `results=1`) via `scripts/live_check/openalex_smoke.py`.
- **Settings source-test endpoint (`/v1/settings/agent_tools/test_source`):**
  - `openalex`: green (`ok=true`, `detail=ok:results=1`)
  - `semantic_scholar`: non-green (`ok=false`, `detail=http_429`)
  - `mcp`: green after persisted adapter URL patch (`ok=true`, `detail=ok`)
