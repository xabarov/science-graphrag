# Agent tools constants — inventory (2026-05-07)

Purpose: classify knobs in `science_graphrag/agent/tools` so operator/runtime settings, public tool contracts, and internal guardrails stay distinct.

## Classification legend

| Class | Meaning |
|-------|---------|
| **R** | Runtime / operator (`Settings`, env `SCIENCE_GRAPHRAG_*`, optional future admin persisted section) |
| **P** | Public contract (`Pydantic` `Field`, tool args defaults and `ge`/`le`) |
| **G** | Internal guardrail (trace preview, error string cap, Phoenix span preview, IO polling) |

## Cross-cutting

| Location | Values | Class | Notes |
|----------|--------|-------|-------|
| [`chunk_retrieval_defaults.py`](../../science_graphrag/agent/tools/chunk_retrieval_defaults.py) | `DEFAULT_AGENT_CHUNK_TOP_K`, `MAX_AGENT_CHUNK_TOP_K`, `normalize_agent_retrieval_query` | **P** + shared policy | Single place for idea/paper_quote top-k alignment |
| Same module (post-2026-05-07) | Trace chars, snippet caps, workspace sample defaults | **G** / **P** | Documented rationale in module docstring |
| [`base.py`](../../science_graphrag/agent/tools/base.py) | Tool span string preview **200** chars | **G** | Phoenix / observability only |

## Per-file summary

### `web_research_tools.py`

| Item | Class | Notes |
|------|-------|-------|
| `agent_web_research_tools_enabled`, `agent_web_fetch_max_bytes`, `agent_web_fetch_cache_ttl_seconds` | **R** | `config.py` |
| `agent_web_search_http_timeout_seconds`, `agent_web_fetch_http_timeout_seconds` | **R** | `config.py` — operator HTTP budgets for Crossref vs streamed GET (defaults 20s / 25s) |
| `_DEFAULT_ACADEMIC_HOST_SUFFIXES` | **R**/policy | Product default allowlist; not UI today |
| `WebSearchArgs` / `WebFetchArgs` (`max_length`, `max_results`, defaults) | **P** | LLM-facing contract |
| Decode / excerpt / summary / fallback char caps, cache-key prompt slice, trace previews, Crossref `rows` cap, `max_redirects`, summarization `max_tokens` when not in Settings | **G** | Named module constants (`WEB_*`) |

### `doi_resolver_tool.py`

| Item | Class |
|------|-------|
| Crossref GET timeout | **R** — uses ``Settings.agent_web_search_http_timeout_seconds`` (same as ``web_search``) |
| Polite-pool mailto fallback | **R** — shared ``OPENALEX_MAILTO_FALLBACK`` in [`openalex.py`](../../science_graphrag/ingestion/enrichment/openalex.py) (must match ``Settings.openalex_mailto`` default) |
| Span `doi_or_url[:120]`, OpenAlex paths | **G** |
| `abstract[:4000]` in metadata | **G** |

### `mcp_surface.py` / `lsp_surface.py` / `runtime_monitor_surface.py`

| Item | Class |
|------|-------|
| `agent_mcp_request_timeout_seconds`, LSP timeouts / max items, monitor tail | **R** |
| `detail[:400]`, LSP `select`/`sleep`, `proc.wait(2.0)` | **G** |

### Retrieval: `idea_search.py`, `paper_quote_search_tool.py`

| Item | Class |
|------|-------|
| `top_k` clamps via `DEFAULT_AGENT_CHUNK_TOP_K` / `MAX_AGENT_CHUNK_TOP_K` | **P** |
| Snippet / quote text lengths | **G** (centralized in `chunk_retrieval_defaults` with docstring: idea = short browse; quote = longer for citations) |
| Trace `query[:200]` | **G** |

### Workspace / catalog: `workspace_catalog_tools.py`, `summarize_workspace.py`, `workspace_paper_tools.py`

| Item | Class |
|------|-------|
| `list_limit` / `find_works` limits / `paper_profile` abstract cap | **P** + **G** |
| Scoped `find_works` `limit * 3` prefetch | **G** (heuristic) |
| Blurb / `summarize_workspace` sample work count | **G** (shared default **8**, max **15**) |
| `find_works` trace `query[:240]` | **G** |

### Graph tools: `cypher_query.py`, `edge_search.py`, `entity_search.py`

| Item | Class |
|------|-------|
| `max_rows` / `LIMIT` examples / `limit` caps | **P** + **G** |
| Span truncations (`query[:400]`, `rel_types[:12]`, `query[:240]`) | **G** |

### `product_interaction_tools.py`

| Item | Class |
|------|-------|
| Pydantic `max_length` on plan / questions / brief | **P** |
| `brief` output cap **240** | **P** (product contract) |

## Quality-sensitive / heuristic-looking (watch list)

- **`web_research_tools`**: raw HTML decode cap vs LLM excerpt vs summary caps — strongly affects summarization quality; should stay documented and named.
- **`idea_search` snippet (240) vs `paper_quote_search` snippet (400) and quote (800)`**: intentional asymmetry; document in `chunk_retrieval_defaults` (done in code comments).
- **`find_works` scoped `limit * 3`**: recall vs cost tradeoff; keep as explicit constant if tuned later.

## Related docs

- Admin UI surface proposal (separate persisted `agent_tools` section): [`agent-tools-admin-settings-proposal-2026-05-07.md`](./agent-tools-admin-settings-proposal-2026-05-07.md)
- Backlog: `[OPEN] Persisted admin section agent_tools` in [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md)
