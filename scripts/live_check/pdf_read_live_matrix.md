# PDF read live matrix (operator checklist)

Run from repo root after `make dev-up`, `.venv/bin/science-graphrag config-check`, and explicit `AGENT_LIVE_BASE` / `AGENT_LIVE_WORKSPACE_ID` per `docs/analysis` live-check runbooks.

## Preflight

1. `COMPOSE_FILE=docker-compose.dev.yml:docker-compose.live-check.yml docker compose ps` — `api` healthy.
2. `export AGENT_LIVE_BASE=http://127.0.0.1:18787` (or your stable contour).
3. Smoke: `.venv/bin/python scripts/live_check/agent_v2_http.py --base-url "$AGENT_LIVE_BASE" --workspace-id "$AGENT_LIVE_WORKSPACE_ID" --timeout 5`

## Matrix (manual)

| Case | Request body snippet | Expect |
|------|----------------------|--------|
| arXiv PDF | `"pdf_read_request":{"pdf_url":"https://arxiv.org/pdf/1706.03762.pdf"},"question":" "` (or token `__sg_pdf_read_action__`) | SSE shows `pdf_read_*` steps; `pdf_read_extracting` may include `pdf_read_artifact_id` / `pdf_read_ok`; `final_answer.run_metadata` includes stable `pdf_read_artifact_id` (+ optional `pdf_read_tool_ok` / `pdf_read_tool_error`); answer cites extracted text or tool trace `read_external_pdf` ok |
| Backend modes | PATCH `/v1/settings/agent_tools` `agent_pdf_read_backend_mode`: `pypdf` / `vl` / `hybrid`; repeat same PDF query | `run_metadata.agent_pdf_read_backend_mode` matches setting; on success prefetch/tool payload includes `read_backend` + `fallback_used`; `hybrid` uses VL when pypdf excerpt is empty or very short (VL key required for `vl` / `hybrid` fallback) |
| OA landing | Valid Unpaywall `oa_pdf_url` from a known OA DOI | Same; may hit publisher redirect policy |
| Blocked / private | `"pdf_url":"https://127.0.0.1/x.pdf"` | `private_host_not_allowed` / policy error in trace; citation fallback when hydrated |

## curl (SSE)

```bash
curl -N -H 'Accept: text/event-stream' -H 'Content-Type: application/json' \
  -d '{"question":"__sg_pdf_read_action__","workspace_id":"'"${AGENT_LIVE_WORKSPACE_ID}"'","pdf_read_request":{"pdf_url":"https://arxiv.org/pdf/1706.03762.pdf"},"web_research_enabled":true}' \
  "${AGENT_LIVE_BASE}/v2/agent/query"
```

Record a short trace snippet (first `product_step` lines + final `final_answer` head) for review docs.
