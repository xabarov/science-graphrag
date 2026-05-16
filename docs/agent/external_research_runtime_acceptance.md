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

- MCP adapter smoke: pending contour config (`SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL` missing in current lane).
- Semantic Scholar smoke: observed `403 Forbidden` in current lane (failure contract validated; source remains `needs_live_smoke`).
- OpenAlex smoke: green (`http_status=200`, `results=1`) via `scripts/live_check/openalex_smoke.py`.
