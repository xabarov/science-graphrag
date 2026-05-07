# Proposal: persisted `agent_tools` settings (admin) — 2026-05-07

## Problem

Many **operator-relevant** tool knobs already exist on `Settings` (`SCIENCE_GRAPHRAG_*`) but only a subset flows through [`SettingsService`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/settings/service.py) and `/v1/settings`. Today, **LLM advanced** (`PATCH /v1/settings/llm` → `runtime_overrides`) is the main persisted surface; overloading it with MCP/LSP/web-fetch argv-style data would mix concerns and complicate validation.

## Recommendation

Add a dedicated persisted bucket, e.g. `data/settings/*.json` key **`agent_tools`**, with its own:

- `GET /v1/settings` snapshot field `agent_tools: { ... persisted fragments, effective: {...} }`
- `PATCH /v1/settings/agent_tools` (or nested route) with a small typed request model
- `build_non_secret_overrides()` merge: map only whitelisted flat keys into `Settings` model fields (same pattern as `llm` → `extraction_llm_*` today)

### First-wave fields (safe scalars)

| Setting field | Rationale |
|---------------|-----------|
| `agent_web_research_tools_enabled` | Surface toggle |
| `agent_web_fetch_max_bytes` | Abuse / memory cap |
| `agent_web_fetch_cache_ttl_seconds` | Freshness vs cost |
| `agent_web_search_http_timeout_seconds` | Crossref SLO tuning |
| `agent_web_fetch_http_timeout_seconds` | Streamed fetch SLO tuning |
| `agent_mcp_tools_enabled` + `agent_mcp_request_timeout_seconds` | Integration toggles |
| `agent_lsp_tool_enabled` + `agent_lsp_request_timeout_seconds` + `agent_lsp_max_result_items` | Bounded LSP |

### Defer or keep env-only

| Field | Rationale |
|-------|-------------|
| `agent_lsp_server_argv` | Arbitrary spawn — platform / secret manifest, not casual admin UI |
| `agent_mcp_server_denylist`, `agent_tool_search_llm_pre_denylist` | List validation + size caps + migration story |

### Non-goals

- Do **not** expose internal truncation (`snippet[:240]`, Phoenix preview 200) as admin knobs.
- Do **not** add string-budget sliders for `web_fetch` LLM excerpt unless backed by eval + clear product promise.

## Implementation sketch

1. Extend [`SettingsRepository`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/settings/repository.py) schema with optional `agent_tools` dict (backward compatible).
2. [`build_non_secret_overrides()`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/settings/runtime_overlay.py): merge `agent_tools` → `Settings` update dict for allowlisted keys only.
3. [`SettingsService.get_snapshot()`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/settings/service.py): add `agent_tools` section with `effective` mirrors + `_meta`.
4. [`get_schema()`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/settings/service.py): bump schema `version`, add `agent_tools` section fields (booleans, numbers, bounded ranges from pydantic metadata).
5. API: [`api/settings.py`](/home/roman/pyprojects/ML/Prod/science-graphrag/science_graphrag/api/settings.py) + pydantic request models.
6. UI: new card under Settings (admin-gated) mirroring schema; reuse numeric min/max from schema response.

## Acceptance (when implemented)

- Changing a scalar in admin UI round-trips into `get_settings()` used by API workers after reload/restart policy documented.
- No secrets in `agent_tools` JSON; argv-like vectors remain env-only.
- Cross-field validators extended if new timeouts must satisfy `agent_step_timeout_seconds` etc.

## Status

**Design only** as of 2026-05-07; tracked in backend backlog until a dedicated refactor pass.
