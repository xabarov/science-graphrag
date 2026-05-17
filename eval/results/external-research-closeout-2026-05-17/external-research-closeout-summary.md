# External Research Closeout Summary (2026-05-17)

## Scope

- External-only acceptance scope: Crossref/web, arXiv, Unpaywall, OpenAlex, Semantic Scholar, PDF read surface, MCP integration lane.
- Live contour: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Artifact root: `eval/results/external-research-closeout-2026-05-17/`

## Overall verdict

- **Go/No-Go:** `NO-GO` for full external-research closeout as production-proven in this contour.
- Reason: non-green lanes remain in routing/policy/config completeness:
  - OpenAlex lane did not invoke `openalex_works_search`
  - PDF lane denied `read_external_pdf` in tool-surface policy
  - MCP lane missing adapter base URL + missing `mcp_audit_summary` in E2E run

## Per-lane status

- `external_web`: **pass**
  - official sources + web fetch + scholarly corroboration observed
  - Phoenix trace fetched successfully
- `arxiv`: **pass**
  - `arxiv_search` and fetch path observed
  - Phoenix trace fetched successfully
- `unpaywall`: **pass**
  - `unpaywall_lookup` observed; graceful fallback behavior preserved
  - Phoenix trace fetched successfully
- `semantic_scholar`: **pass**
  - `semantic_scholar_search` + `semantic_scholar_paper` observed
  - direct API smoke and source-test endpoint are green
- `openalex`: **fail**
  - expected tool missing in lane (`openalex_works_search`)
  - provider smoke and source-test endpoint are green (points to routing issue)
- `pdf_read`: **fail**
  - default lane did not trigger `read_external_pdf`
  - forced lane triggered tool name but denied by policy (`not_in_bound_tool_surface`)
- `mcp_adapter_smoke`: **fail** (`missing_base_url`)
- `mcp_agent_e2e_smoke`: **fail** (`mcp_audit_summary=null`)

## Phoenix integrity summary

- All per-lane Phoenix pulls succeeded (`fetch_ok=true` in each `*-phoenix.jsonl`).
- Span-level mismatch is functional (tool-selection/policy), not telemetry transport.

## Deferred / follow-up actions

- OpenAlex routing intent tuning:
  - ensure external-discovery prompts select `openalex_works_search` when expected.
- PDF policy alignment:
  - align `pdf_read_request` + `read_external_pdf` availability in live contour bound tool surface.
- MCP contour completeness:
  - set `SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL` for lane
  - restore/verify `run_metadata.mcp_audit_summary` in E2E path.

## Owner-ready remediation queue

1. **Routing:** OpenAlex prompt family route policy (`retrieval_agent` shortlist / rules).
2. **Policy:** PDF tool-surface allowlist for explicit pdf-read action.
3. **Ops config:** MCP adapter URL + E2E audit aggregation verification.
4. **Re-run:** execute `scripts/live_check/external_research_closeout.py` after fixes and require `closeout_gate_status=pass`.
