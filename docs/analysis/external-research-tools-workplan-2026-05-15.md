# External Research Tools Workplan

Date: 2026-05-15

Companion docs:

- Architecture decision: `docs/adr/030-external-research-tools-architecture.md`
- Implementation review/status: `docs/analysis/external-research-tools-implementation-review-2026-05-15.md`
- Landscape scan: `docs/analysis/sci-tools.md`
- Backlog anchor: `docs/backlog/refactor-backend.md` → `[OPEN] External research: OpenAlex search + Semantic Scholar tools`

## Goal

Make external scholarly tools useful in chat without turning the product into a pile of switches:

- stable default tools work without user configuration;
- external calls are clear, bounded, and explainable;
- source provenance and evidence quality are visible;
- PDF/full-text work is explicit, cached, and recoverable;
- operator settings and API keys are manageable from one clean settings panel.

## Non-Goals

- Do not build a full MCP research hub in the native path.
- Do not make PDF extraction a thin extension of `arxiv_fetch`.
- Do not expose every backend `Settings` field directly in the UI.
- Do not add duplicate OpenAlex-by-DOI tools; `doi_resolver` owns DOI metadata resolution.

## Workstreams

Keep future PRs in three independent workstreams:

1. **Metadata/Search** — Crossref/arXiv/Unpaywall stabilization, OpenAlex search, Semantic Scholar search.
2. **Full Text** — PDF download/read/extract, artifact lifecycle, section evidence.
3. **Tools UX / Operations** — settings panel, source diagnostics, outbound policy, provenance labels.

## Phase 0 — Stabilize Current Tools

Purpose: make the already-implemented external tools observable and safe before adding more APIs.

### Scope

- `web_search`
- `web_fetch`
- `arxiv_search`
- `arxiv_fetch`
- `unpaywall_lookup`
- `doi_resolver` (as separately gated metadata bridge)

### Backend

- Add optional live smoke checks for:
  - Crossref `web_search`
  - arXiv search/fetch
  - Unpaywall lookup on a known DOI
- Add source diagnostics payload for Settings snapshot:
  - `enabled`
  - `available`
  - `configured`
  - `requires_key`
  - `status`
  - `last_test`
  - `last_error`
- Normalize failure reason vocabulary for external tools:
  - `source_unreachable`
  - `rate_limited`
  - `host_not_allowed`
  - `redirect_blocked`
  - `metadata_only_fallback`

### Frontend

- Rename composer tooltip/copy from “web search” to **external sources**.
- Keep one compact external-sources button in composer.
- Show source diagnostics in detailed trace/settings, not as extra composer controls.

### Tests

- Mock-backed tests for failure reason mapping.
- Regression: external disabled denies external research tools.
- Optional live lane, not default CI.

### Acceptance

- Current unit tests remain green.
- `unpaywall_lookup` and Crossref have at least one documented live smoke result or explicit “not live-validated” status.
- UI copy no longer implies generic Google-like search.

## Phase 1 — Agent Tools Settings Panel

Purpose: turn the existing `agent_tools` section from a placeholder/operator slice into a usable control surface.

### Backend

Extend `runtime_settings.json.agent_tools` and `UpdateAgentToolsSettingsRequest` gradually with allowlisted fields:

- `external_research_default_enabled`
- `external_research_sources`
- `pdf_reading_mode`
- `agent_unpaywall_oa_tool_enabled`
- selected limits:
  - external request timeout
  - max external calls per turn
  - max source cards
  - future PDF bytes/pages/timeouts

Keep secret values out of runtime overrides. Add dedicated secret-store keys only when needed:

- `agent_tools.semantic_scholar_api_key`
- `agent_tools.ncbi_api_key`
- MCP credentials via MCP auth/server layer, not a generic global key.

### Frontend

Implement `AgentToolsSettingsPanel` under Settings:

- **Research sources** card:
  - External scholarly sources main switch.
  - Crossref, arXiv, Unpaywall rows with status chips.
  - Planned rows for OpenAlex and Semantic Scholar.
- **Full-text / PDF** card:
  - `PDF reading in chat`: `Off` / `Ask before reading` / `Auto for safe OA/arXiv PDFs`.
  - Advanced limits collapsed.
- **Integrations** card:
  - MCP tools off by default.
  - MCP adapter URL / denylist in advanced.
- **Credentials & diagnostics** card:
  - contact email / polite-pool mailto status.
  - per-source test buttons.
  - last tested / last error.

### UX Rules

- Ordinary user controls: external sources default, PDF reading mode, beta source toggles.
- Admin/operator controls: keys, MCP, limits, outbound policy, source availability defaults.
- Do not expose arXiv vs Crossref as ordinary per-turn toggles.

### Tests

- API PATCH validation for new allowlisted fields.
- Settings snapshot includes source status rows.
- Frontend tests for card rendering and dirty/save behavior.

### Acceptance

- `agent_tools` Settings section is no longer placeholder-only.
- Users can understand which sources are on, stable, beta, planned, or need configuration.
- No secrets are returned to the UI.

## Phase 2 — Trust Model and Failure UX

Purpose: make answers honest about what evidence they used.

### Backend

- Add/derive evidence quality labels:
  - `strong`
  - `medium`
  - `weak`
  - `variable`
- Add source/provenance labels:
  - `Workspace full text`
  - `Workspace metadata`
  - `Extracted PDF text`
  - `arXiv abstract`
  - `Crossref metadata`
  - `OpenAlex metadata`
  - `Unpaywall OA link`
  - `Web page summary`
  - `MCP external source`
- Ensure writer instructions distinguish metadata-only from full-text evidence.

### Frontend

- Show compact badges on source/citation cards:
  - `full text`
  - `abstract`
  - `metadata only`
  - `external`
  - `PDF read`
- Show fallback reason near the source card when a tool fails.

### Tests

- Metadata-only answer does not claim full-text reading.
- PDF unavailable produces clear fallback.
- Source labels match payload type.
- Writer prefers strong evidence over weak metadata.

### Acceptance

- User can tell whether an answer is based on full text, abstract, metadata, or a web summary.
- Tool failures degrade the answer instead of becoming blanket refusals.

## Phase 3 — OpenAlex Works Search

Purpose: add broad literature discovery without duplicating `doi_resolver`.

### Backend

- Add native tool: `openalex_works_search`.
- Source family: `openalex`.
- Use `external_research_user_agent`.
- Support bounded filters:
  - query
  - year range
  - max results
  - maybe open-access filter later
- Return citation-compatible payload:
  - `items`
  - `web_sources`
  - `evidence_origin: "external_web"`
  - `row_count`

### Routing / Policy

- Add manifest row and product step mapping.
- Add source row to `EXTERNAL_RESEARCH_TOOL_NAMES` if governed by external toggle.
- Add shortlist/intent rules only if needed; broad web/external intent may be enough.

### Tests

- Mock HTTP success/failure.
- Manifest/registry/product-step sync.
- External disabled denylist.
- Optional live smoke with a stable query.

### Acceptance

- Agent can discover papers outside workspace via OpenAlex search.
- DOI lookup still goes through `doi_resolver`, not the new search tool.

## Phase 4 — PDF Read / Extract Pipeline

Purpose: enable full-text reading from external PDFs without hidden long-running side effects.

### Backend

- Add a separate PDF read/extract pipeline, not an `arxiv_fetch` extension.
- Suggested tool/API shape:
  - `pdf_read_request`
  - `extract_pdf_text`
  - or an async artifact job API if extraction can exceed normal tool budgets.
- Implement:
  - allowlist/SSRF checks;
  - byte/page limits;
  - parser timeout;
  - heartbeat/progress events;
  - cancellation;
  - cache/reuse by content hash;
  - artifact metadata.

### Frontend

- Add source-card actions:
  - `Прочитать PDF`
  - `Извлечь текст`
  - `Открыть источник`
- Add compact progress artifact card:
  - downloading;
  - extracting;
  - detecting sections;
  - ready;
  - failed with reason.
- Do not add PDF buttons to composer.

### Settings

- Add `PDF reading in chat` mode:
  - `Off`
  - `Ask before reading`
  - `Auto for safe OA/arXiv PDFs`
- Default:
  - local research workspace: `Ask before reading`;
  - privacy-sensitive deployment: `Off`.

### Tests

- PDF unavailable fallback.
- Too-large PDF blocked.
- Same URL/content hash reused.
- Artifact delete path.
- Writer cites extracted text as stronger evidence than metadata.

### Acceptance

- Explicit PDF read request produces progress + artifact + evidence-backed answer.
- Agent never silently claims full-text reading when extraction did not happen.

## Phase 5 — Semantic Scholar

Purpose: add citation-aware discovery once current sources and trust model are stable.

### Backend

- Add first:
  - `semantic_scholar_search`
  - `semantic_scholar_paper`
- Add later:
  - `semantic_scholar_references`
  - `semantic_scholar_citations`
- Add optional API key support for higher limits.
- Keep payloads bounded; avoid dumping citation graph by default.

### Frontend / Settings

- Mark source as beta until live-tested.
- Show optional API key status.
- Add diagnostics/test button.

### Tests

- Mock HTTP for search/paper.
- Optional key vs no-key behavior.
- Rate-limit/failure fallback.

### Acceptance

- Agent can fetch citation-aware paper cards.
- Citation graph tools do not overwhelm context or UI.

## Phase 6 — MCP and External Integrations

Purpose: keep MCP available for advanced integrations without making native tools depend on it.

### Backend

- Keep MCP tools off by default.
- Add per-server diagnostics.
- Clarify auth flow:
  - OAuth / token managed by MCP layer;
  - no generic global “MCP API key”.
- Enforce server denylist and timeout.

### Frontend

- MCP lives under Settings → Agent Tools → Integrations.
- Show connected/unconfigured/denied states.
- Keep raw MCP details in advanced/detailed mode.

### Acceptance

- Native arXiv/Crossref/Unpaywall/OpenAlex flows work without MCP.
- MCP failures do not degrade native external tools.

## Cross-Cutting Policies

### Outbound Policy

Add explicit product semantics:

- `external_research_enabled`: scholarly external sources in chat.
- `outbound_http_policy`: deployment-level operator policy.
- Keep `web_research_enabled` as compatibility alias.

### Budgets

Define and test:

- max external calls per turn;
- max PDF reads per turn;
- max external wall time;
- max source cards by default;
- partial answer behavior.

### Privacy Copy

UI should clearly say:

- external sources send queries to third-party scholarly APIs;
- local mode stays within workspace/corpus;
- PDF read downloads and stores a local artifact.

## PR Slicing

Recommended order:

1. **PR 1: Naming + diagnostics groundwork**
   - external source copy;
   - source status snapshot;
   - live smoke hooks.
2. **PR 2: Agent Tools Settings Panel**
   - frontend panel;
   - PATCH allowlist expansion;
   - source status chips.
3. **PR 3: Trust labels + failure UX**
   - provenance/evidence quality;
   - source card badges;
   - writer safeguards.
4. **PR 4: OpenAlex search**
   - native tool + tests + docs.
5. **PR 5+: PDF pipeline**
   - artifact model;
   - extraction job/tool;
   - chat actions/progress.
6. **PR 6+: Semantic Scholar**
   - search/paper first;
   - citations/references later.

## Definition of Done

For each new external tool:

- manifest row with `source_family`;
- Settings/source status row;
- external toggle/denylist decision documented;
- product step mapping;
- mock HTTP tests;
- failure reason tests;
- optional live smoke if source supports it;
- source provenance label;
- docs updated in implementation review and this workplan.

