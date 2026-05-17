# ADR 030: External research tools — architecture and extension path

- **Status**: Accepted
- **Date**: 2026-05-15

## Context

The agent retrieval surface mixes **workspace/corpus tools** (Neo4j, Qdrant) with **external HTTP research** (Crossref, arXiv Atom, optional OA lookup). `docs/analysis/sci-tools.md` catalogs many MCP servers and hypothetical tool names; we need a **stable in-repo architecture** so new sources (OpenAlex search, Semantic Scholar, Unpaywall, PubMed, …) do not inflate `build_retrieval_tools` or fragment timeouts, User-Agent policy, citation payloads, and denylist logic.

## Decision

1. **Package boundary** — All HTTP-backed “external literature” tools are assembled through `science_graphrag.agent.tools.external.build_external_research_tools` (see `external/__init__.py`). `build_retrieval_tools` calls this factory instead of inlining `build_web_research_tools` + `build_arxiv_tools` + future modules.

2. **Shared transport policy** — `science_graphrag.agent.tools.external.http_transport.external_research_user_agent` centralizes the polite-pool `User-Agent` (mailto from `Settings.openalex_mailto` with the same fallback as ingestion OpenAlex). Crossref `web_search`, streamed `web_fetch`, arXiv, Unpaywall, and Crossref fallback inside `doi_resolver` use this helper. Individual tools still choose timeouts via existing `Settings` fields (e.g. `agent_web_search_http_timeout_seconds`) until a dedicated `agent_external_http_timeout_seconds` is justified.

3. **Evidence contract** — External tools keep returning payloads aligned with the citation path: `evidence_origin: "external_web"`, `web_sources` where applicable, `ok` / `error` / `row_count` (see `web_research_tools`, `arxiv_tools`, `unpaywall_tools`).

4. **Manifest taxonomy** — `ToolManifestEntry` gains an optional `source_family: str | None` (e.g. `crossref`, `arxiv`, `unpaywall`) for documentation and future shortlist tuning; scoring may use it later without changing tool names.

5. **Operator gating** — New external tools use `Settings` feature flags (pattern: `agent_*_tool_enabled`). The global user toggle `web_research_enabled` continues to map to `EXTERNAL_RESEARCH_TOOL_NAMES` in `request_turn_policy` (canonical name; `WEB_RESEARCH_TOOL_NAMES` remains a backward-compatible alias).

6. **MCP vs native** — Heavy “research hub” parity with third-party MCP servers stays **optional** behind `agent_mcp_tools_enabled`. Native tools remain bounded, testable without MCP, and CI-friendly.

## Consequences

- New external tools: implement module under `agent/tools/external/` (or keep legacy path but register only via `build_external_research_tools`), add manifest row with `source_family`, extend denylist set if user-toggle applies, add unit tests with `httpx` mocks.
- **Not in this ADR**: PDF full-text extraction, Semantic Scholar graph, reading-list session state — tracked in `docs/backlog/refactor-backend.md` under external-research follow-ups.
- **Docs**: `docs/analysis/sci-tools.md` links here for architecture; product-facing tool lists stay in code + manifest.

## References

- `science_graphrag/agent/tools/external/`
- `science_graphrag/agent/tool_manifest.py`
- `science_graphrag/agent/request_turn_policy.py` (`EXTERNAL_RESEARCH_TOOL_NAMES`)
- `docs/analysis/sci-tools.md`
- **Agent behavior on top of these tools (prompt protocol, `final_answer`, observability):** [`smolagents-prompt-patterns-for-agent-runtime-2026-05-17.md`](../analysis/smolagents-prompt-patterns-for-agent-runtime-2026-05-17.md)
