# Phoenix analysis — external research closeout (2026-05-17)

## Scope

- Base URL: `http://127.0.0.1:18787`
- Workspace: `ws-pilot-od`
- Source pack: `eval/results/external-research-closeout-2026-05-17/`
- Trace snapshots: `*-phoenix.jsonl`

## Lane-by-lane findings

### external_web

- Gate: `pass`
- Expected tools present in `tool_trace`: `official_web_lookup`, `web_fetch`
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Signal quality:
  - official-tier URLs present in citations (`ultralytics.com`, `docs.ultralytics.com`, `github.com/ultralytics`)
  - failure contract observed for a blocked fetch path (`doi.org` -> `403`) with fallback metadata citations
- Conclusion: lane is healthy for official-source pass + negative-claim guard.

### arxiv

- Gate: `pass`
- Expected tools present: `arxiv_search` (plus follow-up `arxiv_fetch`)
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Failure contract: no transport/rate-limit failures in this run.
- Conclusion: lane is healthy for search/fetch metadata flow.

### unpaywall

- Gate: `pass`
- Expected tools present: `unpaywall_lookup`
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Failure contract:
  - `unpaywall` endpoint returned non-200 in debug events (`status: 0`) for one DOI path
  - answer continued with metadata fallback (degradation instead of hard refusal)
- Conclusion: fallback behavior is valid; live availability remains variable per DOI/provider.

### openalex

- Gate: `fail` (`missing_expected_tools:openalex_works_search`)
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Observed behavior:
  - route stayed on workspace tools (`find_works`, `paper_profile`) and did not invoke OpenAlex tool
  - direct provider smoke is green (`openalex_api_smoke.json`)
  - settings source-test is green (`openalex-source-test.json`)
- Additional forced lane:
  - `openalex-forced-smoke.json` still did not execute `openalex_works_search`
- Conclusion: issue is routing/tool-selection policy for this prompt class, not provider transport.

### semantic_scholar

- Gate: `pass`
- Expected tools present: `semantic_scholar_search` (plus `semantic_scholar_paper`)
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Failure contract:
  - duplicate-paper call warning detected (`duplicate_tool_batch_signature`) with safe forced finalization
  - no transport failure; provider/API-key lane is green
- Conclusion: lane healthy with minor optimization opportunity (avoid duplicate paper call).

### pdf_read

- Gate: `fail` (`missing_expected_tools:read_external_pdf`)
- Phoenix integrity: `fetch_ok=true`, `span_count=100`
- Observed behavior:
  - primary lane used `arxiv_fetch` and denied it due to turn denylist
  - forced lane (`pdf-forced-smoke.json`) invoked `read_external_pdf`, but tool was denied (`not_in_bound_tool_surface`)
- Conclusion: PDF tool registration/allow-surface policy mismatch in live contour; not a transport failure.

## MCP integration checks

- `mcp_adapter_smoke.json`: fail (`missing_base_url`)
- `mcp_agent_e2e_smoke.json`: fail (`mcp_audit_summary=null`)
- Interpretation:
  - adapter base URL was not configured for this run
  - even with `call_mcp_tool` in trace, aggregated `run_metadata.mcp_audit_summary` was absent
- Conclusion: MCP lane is non-green in current contour and blocks full external closeout.

## Overall verdict

- Phoenix fetch integrity is green across all source lanes (`fetch_ok=true` everywhere).
- Functional closeout remains **fail** due to:
  - OpenAlex lane not selecting `openalex_works_search`
  - PDF lane policy denying `read_external_pdf`
  - MCP adapter/audit lane not configured/complete in this contour
