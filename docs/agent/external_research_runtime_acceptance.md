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

## Web evidence quality gates (YOLO11 / product internet research)

Operator lane for **official-source pass**, **source diversity**, and **negative-claim guard**
when users ask to search the open web about a product/model/version (regression: YOLO v11).

### Preconditions

- Dev contour healthy (`make dev-up` or stable live-check API on `http://127.0.0.1:18787`).
- `.venv/bin/science-graphrag config-check` passes.
- `AGENT_LIVE_BASE=http://127.0.0.1:18787`
- `AGENT_LIVE_WORKSPACE_ID=ws-pilot-od` (or your pilot workspace)
- Optional: `PHOENIX_UI_BASE_URL=http://127.0.0.1:16006` for span pull in the smoke artifact.

### Commands

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:18787
export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od

# Unit / contract (CI-safe)
.venv/bin/pytest tests/agent/test_web_evidence_policy.py \
  tests/scripts/live_check/test_external_web_research_validate.py -q

# Live API agent run (requires LLM + external HTTP)
.venv/bin/python scripts/live_check/external_web_research_smoke.py \
  --write-json eval/results/external-web-research-smoke.json

# Optional Phoenix span pull when trace id is printed in the JSON artifact
.venv/bin/python scripts/live_check/phoenix_trace_pull.py \
  --trace-id <phoenix_trace_id> \
  --out-jsonl eval/results/external-web-phoenix.jsonl
```

### Pass criteria

- With `external_research_source_crossref_enabled=false`, retrieval still exposes
  `official_web_lookup` and `web_fetch` (only Crossref `web_search` is omitted).
- `tool_trace` includes `official_web_lookup` **or** citations contain an **official-tier** URL
  (e.g. `docs.ultralytics.com`, `github.com/ultralytics`).
- Final answer does **not** claim “no official announcement/release” without official-source evidence.
- Phoenix tool spans expose `tool.result_ok=false` and `error`/`detail` when `web_fetch` fails (`ok:false` payload).
- Citations are not **only** Crossref `metadata_only` scholarly rows for product/version questions.

## Latest lane snapshot (2026-05-16)

- **MCP adapter smoke:** green (`http_status=200`, `rpc_ok=1`) with host stub `mcp_jsonrpc_stub.py` on port `19999` and `docker-compose.mcp-live-check.yml` API overlay.
- **MCP agent E2E:** green (`mcp_agent_e2e_ok=1`, `call_mcp_tool` in `tool_trace`, `mcp_audit_summary.last.ok=true`) via `scripts/live_check/mcp_agent_e2e_smoke.py` against `AGENT_LIVE_BASE=http://127.0.0.1:18787`.
- **Semantic Scholar smoke:** green after keyed run from `.env` (`search_http_status=200`, `search_results=1`, `paper_http_status=200`, `paper_title=Attention is All you Need`) via `scripts/live_check/semantic_scholar_smoke.py`.
- **OpenAlex smoke:** green (`http_status=200`, `results=1`) via `scripts/live_check/openalex_smoke.py`.
- **Settings source-test endpoint (`/v1/settings/agent_tools/test_source`):**
  - `openalex`: green (`ok=true`, `detail=ok:results=1`)
  - `semantic_scholar`: latest pre-key result was non-green (`ok=false`, `detail=http_429`); rerun source-test after API restart/settings reload to persist green diagnostics.
  - `mcp`: green after persisted adapter URL patch (`ok=true`, `detail=ok`)
