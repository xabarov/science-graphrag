# External Research Tools: ADR 030 vs Implementation Review

**Doc status:** `reference`

**Read hint:** reconciliation note vs ADR 030; execution queue — workplan doc in same folder.

Date: 2026-05-15

This note reconciles three layers:

- `docs/analysis/sci-tools.md` — archived landscape stub (historical long-form content lives in git history).
- `docs/adr/030-external-research-tools-architecture.md` — accepted in-repo architecture for native external HTTP tools.
- Current implementation under `science_graphrag/agent/tools/`, manifest, request policy, routing features, and tests.

Execution plan: `docs/analysis/external-research-tools-workplan-2026-05-15.md`.

## Executive Summary

The current direction is architecturally sound: **native, bounded HTTP tools** cover the stable core, while broad MCP-style research hubs remain optional behind MCP integration. ADR 030 is aligned with the code after the latest cleanup:

- `build_retrieval_tools` delegates native external HTTP tools to `build_external_research_tools`.
- Shared `external_research_user_agent(settings)` is used by Crossref search/fetch flows, arXiv, Unpaywall, and Crossref fallback inside `doi_resolver`.
- External tools return the expected citation-friendly contract: `ok`, `error` where relevant, `row_count`, `evidence_origin: "external_web"`, and `web_sources` where useful.
- The per-turn web toggle now behaves as a broader **external HTTP research toggle** via `EXTERNAL_RESEARCH_TOOL_NAMES`, with `WEB_RESEARCH_TOOL_NAMES` kept as a compatibility alias.

The main gap is not the architecture, but **coverage and evidence level**:

- `arxiv_search` / `arxiv_fetch`, `web_fetch`, `doi_resolver`, and `unpaywall_lookup` have useful mock-backed unit coverage.
- Live/API evidence exists historically for arXiv scenarios, but Unpaywall and Crossref-by-live-network were not yet validated in a live agent trace after the new architecture pass.
- `docs/analysis/sci-tools.md` is a broad landscape note, not a status page; this document is the implementation-status companion.

## Architecture Mapping

| Area | ADR 030 decision | Current code | Assessment |
|---|---|---|---|
| Package boundary | External HTTP tools assembled through `science_graphrag.agent.tools.external.build_external_research_tools` | `agent/tools/external/__init__.py` builds web + arXiv + Unpaywall; `agent/tools/__init__.py` uses this factory in retrieval tools | Good. Keeps `build_retrieval_tools` from becoming a flat import list. |
| Shared transport policy | Centralize polite `User-Agent` via `external_research_user_agent` | Used by `web_research_tools`, `arxiv_tools`, `unpaywall_tools`, and DOI resolver Crossref fallback | Good. Still only covers User-Agent; retries/rate-limit handling remain per-tool / absent. |
| Evidence contract | External tools return citation-compatible payloads | arXiv/web/Unpaywall use `external_web` + `web_sources`; DOI resolver uses metadata payload and `doi_resolved` SSE hint | Good enough, but DOI resolver is a bridge tool and not fully shaped like web evidence. |
| Manifest taxonomy | `ToolManifestEntry.source_family` for external source taxonomy | Present for Crossref/http/arXiv/Unpaywall/OpenAlex | Good. Useful for future docs and scoring, not yet heavily used in scoring. |
| Operator gating | New external tools get Settings flags; user web toggle denies external HTTP tools | `agent_unpaywall_oa_tool_enabled`, `EXTERNAL_RESEARCH_TOOL_NAMES`; `doi_resolver` remains separately gated by `agent_doi_resolver_tool_enabled` | Good. Important nuance: `doi_resolver` is external but not part of the user web toggle because it is separately operator-gated and usually metadata-safe. |
| MCP vs native | Native tools stay bounded; broad hubs remain optional | MCP surface exists separately (`call_mcp_tool`, resources, auth) and is not required for native tools | Good. Avoids binding project correctness to third-party MCP servers. |

## Implemented Tool Status

| Tool | Source | Purpose | Registration / gating | Test evidence | Stability |
|---|---|---|---|---|---|
| `web_search` | Crossref `/works` | Academic metadata search by query, returns title/DOI/URL rows | Always included in external research tools; denied when `web_research_enabled=false` | Mock/unit coverage in `test_external_research_tools.py`; registry/manifest/product-step coverage | **Stable for metadata search**, not a general web search. Live Crossref trace not re-run in this pass. |
| `web_fetch` | Public HTTPS fetch + LLM summary | Fetch and summarize allowed scholarly URLs with SSRF guards, byte cap, cache | Always included in external research tools; denied when `web_research_enabled=false` | Unit coverage for scheme rejection, private hosts, cache key, redirect host safety | **Stable guardrails**, but content quality depends on page structure + summarizer. |
| `arxiv_search` | arXiv Atom API | Search preprints; returns metadata, abstracts, abs/pdf links | Included in external research tools; denied when `web_research_enabled=false`; shortlist keeps it for arXiv intent | Unit coverage for query building and Atom parsing; prior live/API evidence from arXiv work | **Stable** for metadata/abstract search. No PDF extraction by design. |
| `arxiv_fetch` | arXiv Atom API | Fetch one arXiv record by id/URL | Included in external research tools; denied when `web_research_enabled=false`; shortlist keeps it for arXiv intent | Unit coverage for id resolution, fetch, empty feed, unsupported PDF text; prior live/API evidence | **Stable** for metadata/abstract fetch. PDF text explicitly unsupported. |
| `unpaywall_lookup` | Unpaywall v2 | Given DOI, return OA status and best OA landing/PDF URL; does not download PDF | Included when `agent_unpaywall_oa_tool_enabled=true`; denied when `web_research_enabled=false`; shortlist keeps it for OA/Unpaywall intent | Mock-backed unit coverage for invalid DOI, success payload, registry factory flag, shortlist | **Implementation-stable but not live-validated**. Needs one live trace against a real DOI before calling production-proven. |
| `openalex_works_search` | OpenAlex `/works` | Metadata literature discovery by query (+ optional publication year filter) | Included when `external_research_source_openalex_enabled=true`; denied when `web_research_enabled=false` | Mock-backed tests in `tests/agent/test_openalex_works_search_tools.py`; registry/manifest sync | **Stable by unit contract**; optional live smoke still recommended |
| `doi_resolver` | OpenAlex by DOI + Crossref fallback + Neo4j workspace mapping | Normalize DOI/URL, fetch metadata, optionally map to workspace Work id | Separately gated by `agent_doi_resolver_tool_enabled`; not currently in `EXTERNAL_RESEARCH_TOOL_NAMES` | Existing resolver/helper tests and manifest sync when enabled | **Stable as metadata bridge**, but semantically distinct from web-research toggle. |
| `semantic_scholar_search` | Semantic Scholar Graph API | Bounded metadata search | Included when `external_research_source_semantic_scholar_enabled=true`; denied when external research off | `tests/agent/test_semantic_scholar_tools.py`; optional `scripts/live_check/semantic_scholar_smoke.py` | **Beta** — unit-contract stable; operator live smoke recommended |
| `semantic_scholar_paper` | Semantic Scholar Graph API | Single paper card by id/DOI | Same gating as search | Same test module; smoke covers paper lookup | **Beta** — product step `paper_metadata` |

## Not Implemented Yet

The broad tool landscape from `sci-tools.md` includes several categories not yet implemented as native tools:

- `semantic_scholar_citations`, `semantic_scholar_references`: citation graph tools (deferred until bounded graph UX; see backlog `[PARTIAL] External research: Semantic Scholar tools`).
- `pubmed_search` / `pubmed_fetch`: useful for biomedical/clinical domains, lower priority for the current CS/ML-heavy workflows unless corpus direction shifts.
- `biorxiv_search` / `medrxiv_search`: preprint complement for biomedical domains.
- PDF/text pipeline: `download_arxiv_pdf`, `extract_pdf_text`, `get_paper_sections`, `read_arxiv_paper`. This should not be added as a thin HTTP tool; it needs storage, timeouts, parser selection, safety limits, and artifact lifecycle.
- Stateful reading list / export tools: useful later, but should be session/workspace product features rather than ad hoc HTTP tools.

## What Is Architecturally Normal

- **Native before MCP for core workflows.** For `arxiv_search`, Crossref metadata, DOI resolution, and Unpaywall, native tools are easier to test, bound, observe, and deny per request. MCP remains useful as an optional expansion layer.
- **Avoiding duplicate OpenAlex-by-DOI tools is correct.** The current `doi_resolver` already handles DOI normalization + OpenAlex + workspace mapping. A new OpenAlex tool should focus on **search**, not repeating DOI resolution.
- **Keeping PDF extraction out of arXiv fetch is correct.** `arxiv_fetch` returning `unsupported_pdf_text` is a good contract: metadata fetch is fast and bounded; PDF reading is a separate long-running pipeline.
- **Using `source_family` without overfitting routing is correct.** It documents provenance now and can support future scoring without changing public tool names.

## What Can Be Better

### 1. Split `web_research_tools.py`

`web_research_tools.py` mixes Crossref search, URL safety, cache, fetch streaming, and summarization. It is already near the point where adding more sources would hurt readability.

Recommended split:

- `external/crossref_tools.py` — `web_search` or future `crossref_search`.
- `external/web_fetch_tool.py` — SSRF guardrails, cache, byte cap, summary.
- `external/url_policy.py` — host allow/deny/private-IP helpers if more fetch-like tools appear.

Acceptance: behavior unchanged, tests stay green, no module needs to understand both Crossref query parsing and streamed body summarization.

### 2. Add source-specific live smoke checks

Mocked tests are good, but for external APIs we should keep a tiny optional live lane:

- `arxiv_search`: known query, max 1, validate at least one plausible entry or graceful zero.
- `arxiv_fetch`: known stable id, validate metadata fields.
- `unpaywall_lookup`: known DOI with stable OA status, validate `ok` and URL/status fields.
- `web_search`: Crossref query by DOI/title, validate no schema drift.

These should not run in regular unit CI by default; use an explicit live marker or script.

Latest operator evidence (2026-05-16):

- OpenAlex smoke: **green** (`http_status=200`, `results=1`) via `scripts/live_check/openalex_smoke.py`.
- Semantic Scholar smoke: **observed 403 Forbidden** on search in current contour; failure contract behaves correctly and source remains `needs_live_smoke` until a green run is recorded.
- MCP adapter smoke: **pending adapter configuration** (`missing_base_url` guard from `scripts/live_check/mcp_adapter_smoke.py`); expected until `SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL` is set in operator contour.

### 3. Make external API status visible in docs

Keep `sci-tools.md` as a landscape document, but maintain this file as the **implementation status**. When adding a new external tool, update:

- ADR only if the architecture changes.
- This review/status doc if implementation/stability changes.
- `docs/backlog/refactor-backend.md` only for deferred structural work.

### 4. Decide whether `doi_resolver` belongs to the user web toggle

Current behavior is reasonable: `doi_resolver` is operator-gated and not denied by `web_research_enabled=false`. If product semantics become “no outbound HTTP at all this turn,” then `doi_resolver` should move into `EXTERNAL_RESEARCH_TOOL_NAMES` or a second denylist (`external_http_enabled`) should be introduced.

Do not change this implicitly; it affects existing DOI metadata workflows.

## UI / UX Recommendations

The UI should keep external research powerful but quiet. The current Ask composer already has several controls (`Agent` / `Plan`, open standalone, clear chat, web toggle, send), so source-level knobs should **not** be placed as a row of separate buttons in the composer.

Recommended model:

- **Composer: one primary external-research control.** Keep a single compact globe/web button in the composer. It should mean “allow external online research for this turn”, not “enable every research integration forever”.
- **Details in settings, not in the composer.** Per-source toggles belong in Settings (or an advanced popover), not next to the text box.
- **Auto-select tools by intent.** Users should not need to know whether a query needs Crossref, arXiv, or Unpaywall. The router/shortlist should infer this from the question (`asks_for_web_research`, `asks_for_arxiv`, `asks_for_unpaywall`).
- **Explain what happened after the answer.** Use citations/product steps/tool trace to show “used Crossref”, “used arXiv”, “checked Unpaywall” instead of making the user configure it up front.

### Default Tool Availability

| Tool / group | Default | User-facing control | Rationale |
|---|---:|---|---|
| Workspace/corpus tools (`find_works`, `paper_profile`, `paper_quote_search`, `workspace_inspect`) | On | No per-turn toggle | These are the core value of the app and do not leave the local corpus/workspace. |
| Graph tools (`edge_search`, read-only `cypher_query`) | On where allowed by runtime policy | No ordinary user toggle; admin/operator controls only | They are internal evidence tools. Hiding them behind user controls would add confusion. |
| `web_search` + `web_fetch` | Available by default, but controlled by per-turn “external research” toggle | Single composer globe toggle + persisted preference | Useful but can change latency, answer style, and privacy. One simple switch is enough. |
| `arxiv_search` + `arxiv_fetch` | Available by default with external research | No separate ordinary toggle | arXiv should feel like a natural scholarly source, automatically used for arXiv/preprint intent. |
| `unpaywall_lookup` | Available by default with external research | No separate ordinary toggle | It is low-friction DOI enrichment. Users should not have to learn a separate OA-source switch. |
| `doi_resolver` | Operator-gated, recommended on for research workspaces | Admin/settings toggle, not composer toggle | It is metadata infrastructure and workspace mapping, not a “browse the web” action from the user's perspective. |
| MCP tools | Off by default unless configured | Admin/settings section; optional advanced runtime toggle | High variance, auth-dependent, and can expose broad external capabilities. |
| `openalex_works_search` | On by default where `external_research_source_openalex_enabled=true`; part of external research | No separate ordinary toggle | It complements Crossref as normal scholarly discovery; keep optional live-smoke evidence lane. |
| Future Semantic Scholar citation tools | Off or beta until live-tested | Advanced source selector / admin beta toggle | Citation graph can be high-volume, rate-limited, and may require clearer provenance. |
| Future PDF download/read/extract | Off by default until pipeline-grade | Suggested action in chat + admin setting; not a simple composer toggle | Long-running, heavier safety/storage implications. |

### Suggested Settings Shape

Add a compact **“External Research”** settings card rather than many scattered flags:

- **Main switch:** “Allow external scholarly research tools” (`web_search`, `web_fetch`, arXiv, Unpaywall, `openalex_works_search`).
- **Default for new chats:** `On` / `Off` / “Ask each time” (initial recommendation: `Off` for privacy-sensitive installs, `On` for local research workspaces).
- **Sources list (collapsed by default):**
  - Crossref metadata search: On, stable.
  - arXiv metadata/abstracts: On, stable.
  - Unpaywall OA lookup: On, needs live validation label until smoke-tested.
  - OpenAlex search: On by default where enabled; stable by unit contract, optional live-smoke lane.
  - Semantic Scholar: **Phase 5A shipped (2026-05-16)** — `semantic_scholar_search` / `semantic_scholar_paper` as beta with optional API key; references/citations tools still planned.
- **Advanced section:** timeouts, max bytes, MCP tools, PDF extraction, source-specific beta flags.

Do not expose every Settings field directly (`agent_web_fetch_max_bytes`, `agent_unpaywall_http_timeout_seconds`, etc.) in the ordinary user flow. Those are operator knobs.

### Agent Tools Settings Panel

The app already has a backend settings section named `agent_tools`, but today it is mostly an operator slice (`agent_supervisor_max_rounds`) and the frontend can render it as a placeholder. This should evolve into a focused **Agent Tools** panel, not a generic dump of every `Settings` field.

Recommended panel structure:

```text
Agent Tools
├─ Research sources
│  ├─ External scholarly sources        [main switch]
│  ├─ Crossref metadata search          [status: stable]
│  ├─ arXiv metadata / abstracts        [status: stable]
│  ├─ Unpaywall OA lookup               [status: unit-tested / needs live smoke]
│  ├─ OpenAlex search                   [stable-by-contract / optional live smoke]
│  └─ Semantic Scholar search / paper   [beta; optional API key]
├─ Full-text / PDF
│  ├─ PDF reading in chat               [Off | Ask | Auto safe OA]
│  ├─ Max PDF size / pages              [advanced]
│  └─ Parser timeout / cache TTL         [advanced]
├─ Integrations
│  ├─ MCP tools                         [off by default]
│  ├─ MCP adapter URL                   [advanced]
│  └─ Server denylist                   [advanced]
├─ Runtime limits
│  ├─ Supervisor max rounds             [existing]
│  ├─ External request timeout          [advanced]
│  └─ Per-turn external call budget      [future]
└─ Credentials & diagnostics
   ├─ Contact email / polite-pool mailto
   ├─ Provider API key status
   └─ Test buttons per source
```

The visual design should be compact cards with status chips, not a long form:

- Card title, one-sentence purpose, status chip (`stable`, `beta`, `planned`, `needs key`, `needs live smoke`).
- One primary switch per card where it matters.
- Advanced fields collapsed under “Advanced”.
- “Test connection” action per source where live validation is meaningful.
- Inline “last tested” / “last error” diagnostics, not modal alerts.

#### API Keys and Secrets

Different sources have different credential needs:

| Source / tool | Key needed? | Recommended settings UX |
|---|---:|---|
| Crossref `web_search` | No API key; polite `mailto` recommended | Use global contact email (`openalex_mailto` or renamed “Research contact email”). |
| arXiv `arxiv_search` / `arxiv_fetch` | No API key | No credential field; show rate/politeness note only. |
| Unpaywall `unpaywall_lookup` | No API key, but requires email parameter | Use same research contact email; show if email is configured. |
| OpenAlex `doi_resolver` / future search | No API key, but polite `mailto` recommended | Use same research contact email; test with a lightweight known DOI/query. |
| Semantic Scholar | Usually optional API key for higher limits | Add a secret field only when the tool is implemented; show “optional, improves rate limits”. |
| PubMed / NCBI | Optional API key + email/tool params for higher limits | Keep hidden until PubMed tools exist. |
| MCP tools | Depends on server; may need OAuth/API tokens outside this app | Do not ask for generic “MCP API key”; configure per server or via MCP auth flow. |
| PDF extraction | Usually no API key, but may use parser/VL model credentials | Reuse LLM/VL credentials where extraction needs a model; do not duplicate keys. |

Secret handling should follow the existing LLM credentials pattern:

- Never echo saved secrets back to the UI.
- Show `configured`, `environment`, `server-managed`, or `not configured`.
- Allow “replace key” / “remove key” only for secrets managed by the app.
- Keep secret fields out of `llm.runtime_overrides`; add dedicated secret-store keys per source when needed.

Recommended future secret keys:

- `agent_tools.semantic_scholar_api_key`
- `agent_tools.ncbi_api_key`
- `agent_tools.mcp_server.<server_id>.credential_ref` (or keep OAuth/token storage in MCP layer)

Do **not** add API-key fields for Crossref, arXiv, Unpaywall, or OpenAlex unless the provider contract changes.

#### What Should Be User-Controlled

User-facing controls:

- External scholarly sources allowed for chat: yes/no/default.
- PDF reading mode: `Off`, `Ask`, `Auto safe OA`.
- Optional source enablement for beta/high-variance tools.
- Default for new chats: external sources on/off/ask.

Admin/operator controls:

- Timeouts, byte/page limits, cache TTL.
- MCP adapter URL and server denylist.
- API keys/secrets.
- Per-turn call budgets.
- Supervisor max rounds.
- Tool availability defaults by deployment.

Not worth exposing:

- Individual arXiv vs Crossref toggles for normal users.
- Low-level schema/deferred activation flags.
- Prompt/output character budgets.
- Internal retry/trace preview lengths.

#### Backend Shape

The current `agent_tools` PATCH model only allows `agent_supervisor_max_rounds`. A clean extension would be:

- Keep persisted operator settings under `runtime_settings.json.agent_tools`.
- Add allowlisted fields gradually:
  - `external_research_default_enabled`
  - `external_research_sources` (`crossref`, `arxiv`, `unpaywall`, `openalex`, `semantic_scholar`)
  - `pdf_reading_mode`
  - `agent_unpaywall_oa_tool_enabled`
  - selected advanced limits
- Add source status to the snapshot rather than making the UI infer it:
  - `enabled`
  - `available`
  - `configured`
  - `requires_key`
  - `status`
  - `last_test`
  - `last_error`

This keeps frontend simple and prevents the settings screen from reverse-engineering backend feature flags.

### Composer Copy

Current copy says “Веб-поиск”. Given the tool group now includes Crossref, arXiv, and Unpaywall, clearer user-facing wording:

- Short label/tooltip: **“Внешние источники”**
- On tooltip: “Внешние источники включены: Crossref, arXiv, Unpaywall и загрузка разрешённых URL.”
- Off tooltip: “Внешние источники выключены: агент отвечает по рабочей области и локальному корпусу.”

This keeps the button compact while avoiding the false impression that it is generic Google-like web search.

### Right Panel / Research Plan UX

The screenshot shows a right-side research-plan panel with an empty placeholder while the answer already lists web sources. Recommended behavior:

- Keep the panel collapsed or visually quiet when there is no plan.
- If external tools were used, show a tiny “Sources used” row in the answer header or trace summary rather than filling the plan panel.
- When the user asks “поищи в интернете”, seed a lightweight plan only if the agent will actually perform multi-step research. For a single metadata lookup, avoid adding plan noise.
- Use product-step wording like “Ищу внешние источники”, “Проверяю arXiv”, “Проверяю OA-доступ” rather than raw tool names in the main UI; raw names can stay in detailed trace mode.

### PDF Download / Read in Chat UX

PDF work is different from metadata lookup. Search/fetch/OA lookup are short external-tool calls; PDF download + parse can be slow, fail for publisher restrictions, create local artifacts, and consume context. Treat it as a **progressive action**, not as an always-on hidden tool.

Recommended user experience:

1. **Default answer: metadata first.**  
   When the agent finds a paper via arXiv/Crossref/Unpaywall, it should answer from metadata/abstract/web snippets first and clearly say when it did **not** read the full PDF.

2. **Offer an inline action when a PDF is available.**  
   In a web/arXiv source card, show a compact secondary action:
   - “Прочитать PDF”
   - “Извлечь текст”
   - “Открыть источник”

   Only show “Прочитать PDF” when a likely PDF URL exists (`arxiv` PDF link, Unpaywall `oa_pdf_url`, or a safe allowed URL ending in `.pdf` / PDF content-type).

3. **Make PDF read explicit unless the user strongly asked for it.**  
   Auto-trigger PDF reading only when the prompt says things like “прочитай полный текст”, “extract PDF”, “проанализируй разделы”, “дай цитаты из статьи”, or “сравни full text”. For ordinary “найди статьи” / “что известно” prompts, do not download PDFs automatically.

4. **Use a two-step confirmation for risky/heavy cases.**  
   If the PDF is large, from a non-arXiv host, behind redirects, or not clearly open-access, ask a small structured question:
   - “Нашёл PDF. Скачать и извлечь текст? Это может занять до N минут.”
   - Options: `Read PDF`, `Use metadata only`, `Open source`

5. **Show progress as a small artifact card, not chat spam.**  
   A PDF read should create a compact progress card in the answer/side panel:
   - `Downloading PDF`
   - `Extracting text`
   - `Detecting sections`
   - `Ready: abstract / methods / results / references`
   - `Failed: reason + fallback`

   Avoid streaming raw parser logs into the conversation.

6. **Persist the result as an artifact.**  
   Once extracted, the PDF text should become a reusable local artifact attached to the source/work/session:
   - `pdf_url`
   - SHA / content hash
   - parser used
   - extracted text path
   - section map if available
   - extraction timestamp
   - source tool (`arxiv_fetch`, `unpaywall_lookup`, `web_fetch`, etc.)

   The next chat turn should reuse the artifact instead of downloading again.

7. **Distinguish “download”, “read”, and “extract”.**  
   Product copy should avoid pretending they are the same:
   - **Download PDF**: save/caches binary.
   - **Extract text**: parse PDF into text/markdown/sections.
   - **Read in chat**: use extracted text as evidence for the answer.

   In the UI, ordinary users mostly need “Прочитать PDF”; detailed mode can show the underlying steps.

8. **Do not place PDF controls in the composer.**  
   PDF actions should live on source cards and in a small “Sources used” / “Artifacts” area. Composer should stay simple: text input, mode, external-sources toggle, send.

Good chat flow:

```text
User: Найди статью Fundamentals of Object Detection и прочитай полный текст.

Agent:
1. Finds candidate via Crossref/arXiv/OpenAlex.
2. Checks Unpaywall/arXiv for legal PDF.
3. Shows: “Нашёл PDF: Fundamentals of Object Detection. Прочитать PDF?”
4. User confirms.
5. UI shows compact progress artifact.
6. Agent answers with “Full text read” badge and section-grounded citations.
```

For strong explicit requests (“прочитай PDF по этой ссылке”), skip the extra confirmation if the URL is allowed, size is within limits, and the source is clearly safe/open.

Settings recommendation:

- `PDF reading in chat`: `Off` / `Ask before reading` / `Auto for safe OA/arXiv PDFs`.
- Default: **Ask before reading** for local research workspaces, **Off** for privacy-sensitive deployments.
- Advanced limits: max PDF bytes, max pages, parser timeout, per-turn PDF count, cache TTL.
- Beta label until live-tested on arXiv + Unpaywall + one publisher-hosted OA PDF.

Backend/product implication:

- PDF read should be a separate tool/pipeline (for example `pdf_read_request` / `extract_pdf_text`) with artifact persistence and progress events, not an extension of `arxiv_fetch`.
- It should obey long-running operation rules: timeout, progress heartbeat, cancellation, and cache/resume.
- Extracted text should enter evidence flow as local artifact evidence, not as unbounded chat context.

### UI Implementation Priority

1. Rename composer tooltip/copy from “web search” to **external sources**.
2. Add Settings card with one main switch and a collapsed source list.
3. Add status badges in the Settings source list: `stable`, `unit-tested`, `needs live smoke`, `planned`.
4. Keep per-source beta toggles only for future high-variance tools (Semantic Scholar citation graph, MCP, PDF extraction).
5. Do not add more composer buttons unless there is a distinct user intention that cannot be inferred from text.

## Recommended Next Tools

Priority order:

1. **`semantic_scholar_references` / `semantic_scholar_citations`**  
   Add only after paper lookup is stable. Needs result caps and clear citation graph semantics.

2. **PDF extraction pipeline**  
   Do not implement as a small LangChain HTTP tool. Treat as a bounded ingestion/artifact subsystem: download, parse, cache, sectionize, expose excerpts. Needs timeout/checkpoint rules.

3. **PubMed / bioRxiv / medRxiv**  
   Add when the corpus or user workflows need biomedical coverage. These are domain expansions, not core architecture blockers.

## Stable vs Not Yet Proven

Stable enough for normal agent use:

- `web_fetch` guardrails and cache behavior.
- `arxiv_search` / `arxiv_fetch` metadata and abstract flows.
- `openalex_works_search` discovery flow (unit-contract stable; operator live smoke optional).
- `doi_resolver` DOI metadata bridge when enabled.

Stable by unit contract but needing live proof:

- `unpaywall_lookup` against the real Unpaywall API.
- Crossref `web_search` after the shared User-Agent cleanup.

Not implemented / not stable:

- PDF reading and section extraction (core path shipped; Postgres/object-store audit deferred).
- Semantic Scholar citation graph tools (`references` / `citations`).
- PubMed / bioRxiv / medRxiv tools.
- Stateful reading list and export workflow.

## Missing Plan Items / Follow-up Checklist

These are not new tool ideas; they are cross-cutting product/architecture items that make tools trustworthy and operable.

### 1. Outbound HTTP Policy

Decide and document whether “external research disabled” means:

- only deny `web_search`, `web_fetch`, arXiv, Unpaywall and future scholarly HTTP tools; or
- deny **all** outbound HTTP for the turn, including `doi_resolver`, MCP calls, future Semantic Scholar/OpenAlex, and PDF download.

Recommended product model:

- `external_research_enabled`: controls scholarly external sources for normal chat.
- `outbound_http_policy`: operator-level deployment policy (`allow`, `metadata_only`, `deny_all`, future).
- Keep current API field `web_research_enabled` for compatibility, but treat it as UI/API legacy naming.

Acceptance:

- Clear tests for “external disabled => no external research tool calls”.
- A separate test for whether `doi_resolver` is allowed or denied under each policy.
- UI copy says “local corpus only” when outbound is disabled.

### 2. Failure UX and Fallbacks

External tools should fail gracefully without turning the whole answer into a refusal.

Failure categories to standardize:

- `source_unreachable`
- `rate_limited`
- `api_key_missing`
- `host_not_allowed`
- `redirect_blocked`
- `pdf_unavailable`
- `pdf_too_large`
- `pdf_parse_failed`
- `metadata_only_fallback`

Recommended UX:

- Main answer: short, human-readable fallback note.
- Source card: exact reason + action (“open source”, “retry”, “use metadata only”).
- Detailed trace: raw tool error and request metadata.

Acceptance:

- Writer does not claim full-text evidence when only metadata was available.
- UI shows fallback reason near the source, not as a scary global error unless the whole turn failed.

### 3. Provenance and Trust Labels

Every evidence item should carry a source/trust label visible in simple UI and richer in detailed UI.

Recommended labels:

- `Workspace full text`
- `Workspace metadata`
- `Extracted PDF text`
- `arXiv abstract`
- `Crossref metadata`
- `OpenAlex metadata`
- `Unpaywall OA link`
- `Web page summary`
- `MCP external source`

Suggested quality tiers:

| Tier | Evidence type | Writer behavior |
|---|---|---|
| Strong | Workspace quote / extracted PDF quote | Can support concrete claims with citations. |
| Medium | arXiv abstract / paper abstract / structured metadata | Use for summaries, avoid claiming full-text details. |
| Weak | Crossref title/DOI only / search result metadata | Use for discovery lists, not substantive conclusions. |
| Variable | Web page summary / MCP source | State provenance clearly and prefer corroboration. |

Acceptance:

- `web_sources` / citations include `evidence_quality` or a derivable equivalent.
- Final answer can say “metadata only” when quality is weak.

### 4. Source and Latency Budgets

Without budgets, external tools can make chat slow and unpredictable.

Recommended limits:

- max external HTTP calls per turn;
- max external search sources per turn;
- max PDFs per turn;
- max PDF bytes/pages;
- max total external wall-clock time before partial answer;
- max source cards shown by default.

UX behavior:

- If budget is reached, answer with partial evidence and offer “continue with more sources”.
- Use product step `partial_external_budget_reached` / equivalent warning in metadata.

### 5. Artifact Lifecycle

PDF and extracted full text need lifecycle rules before they become a common chat feature.

Plan:

- Store PDF binary and extracted text/sections as artifacts with content hash.
- Attach artifacts to source URL, DOI/arXiv id, workspace/session where appropriate.
- Reuse artifacts on later turns.
- Define TTL / GC / manual delete.
- Mark externally downloaded artifacts separately from user-uploaded corpus files.

Acceptance:

- Same PDF URL is not downloaded repeatedly in a session.
- User/admin can see and delete external artifacts.
- Extracted text is never dumped wholesale into chat context.

### 6. Privacy / Compliance Copy

When external sources are enabled, user prompts or derived search queries may leave the local environment.

UI copy:

- Composer tooltip: “Внешние источники отправляют поисковые запросы сторонним scholarly API.”
- Settings card: “Используйте локальный режим, если вопрос содержит приватные данные.”
- PDF action: “PDF будет скачан с внешнего сайта и сохранён как локальный артефакт.”

Acceptance:

- External toggle has privacy-aware tooltip.
- Settings page explains outbound behavior without alarmism.

### 7. Roles and Permissions

Separate ordinary chat control from operator/admin controls.

Ordinary user:

- enable/disable external sources per turn;
- request PDF read;
- choose metadata-only fallback;
- see source provenance.

Admin/operator:

- configure source availability;
- manage API keys;
- enable MCP;
- set outbound policy;
- tune limits;
- view source diagnostics.

Acceptance:

- Settings API keeps `agent_tools` protected by settings auth.
- Composer does not expose admin-only source flags.

### 8. Evaluation Plan

Add regression cases beyond unit tests:

- arXiv metadata answer does not claim PDF/full-text reading.
- Unpaywall live smoke returns OA URL or graceful not-OA result.
- External disabled prevents external source calls.
- PDF unavailable produces metadata-only fallback.
- Source labels match evidence type.
- Writer ranks full-text evidence over metadata-only evidence.
- “Continue reading PDF?” flow does not lose prior context.

Acceptance:

- Mock-backed CI tests for all policy branches.
- Optional live lane for Crossref/arXiv/Unpaywall/OpenAlex/Semantic Scholar when configured.

### 9. Naming Migration

The product concept is no longer just “web research”.

Recommended migration:

- UI copy: `Внешние источники`.
- New metadata naming: `external_research_enabled`, `external_research_tools`.
- Keep API request field `web_research_enabled` as backward-compatible alias.
- Keep `WEB_RESEARCH_TOOL_NAMES` alias in code until clients move.
- Docs should prefer “external research” / “external scholarly sources”.

Acceptance:

- UI text no longer implies generic Google-like web search.
- API remains backward compatible.

### 10. Roadmap Split

Keep three workstreams separate:

- **Metadata/search:** OpenAlex search, Semantic Scholar search/paper cards, source status.
- **Full text:** PDF download, extraction, artifact lifecycle, section evidence.
- **Integrations:** MCP auth/diagnostics, per-source keys, admin settings.

This prevents the next PR from mixing product UI, source APIs, PDF parsing, and MCP policy in one diff.

## Bottom Line

ADR 030, the current native implementation, and the broader `sci-tools.md` landscape are consistent if read as three different layers:

- `sci-tools.md` answers “what tools exist in the ecosystem and what might be useful?”
- ADR 030 answers “what architecture do we use for native tools in this repo?”
- Current code answers “which bounded subset is implemented and covered now?”

The architecture is in good shape. The next improvement should be either:

1. add live smoke evidence for `unpaywall_lookup` / Crossref / `openalex_works_search`, or
2. execute the operator PDF live matrix (`scripts/live_check/pdf_read_live_matrix.md`) and attach artifacts, or
3. continue toward **Semantic Scholar references/citations** (bounded graph UX) and **Postgres/object-store** durable PDF rows per backlog `[PARTIAL]` items; **Phase 6 MCP operator slice** (integrations snapshot, Settings PATCH for timeout/denylist, smoke) is shipped — see workplan Phase 6 status.

**Execution detail:** Phase 3 **closeout** (optional OpenAlex live smoke, diagnostics `status` decision) and Phase 4 **staged delivery** (PDF artifact pipeline → SSE → trust → Ask UI → live matrix) are spelled out in `docs/analysis/external-research-tools-workplan-2026-05-15.md` (Phase 3 **Remaining / Closeout**, Phase 4 Stages 1–8, PR slicing PR 4b–PR 9). **2026-05-16:** Phase 4 closeout added optional Redis durable cache + stable `artifact_id`; Phase 5A Semantic Scholar search/paper shipped (see workplan Phase 5 status).

## Phase 4 honest closure (2026-05-15) — shipped in repo

- **Typed API:** `PdfReadRequest` + relaxed `question` when `pdf_read_request` is present; machine token `__sg_pdf_read_action__` replaces legacy `"[pdf-read-action]"` in the canonical path.
- **Orchestrator:** `pdf_read_orchestrator.execute_pdf_read` is the single fetch/parse/cache path for `read_external_pdf` and optional SSE prefetch (`pdf_read_validating` / `pdf_read_downloading` / `pdf_read_extracting`) before the LangGraph stream.
- **Pipeline/cache:** `pdf_read_pipeline` (policy + fetch + parse), `BoundedTtlPdfReadCache` (LRU + TTL), operator knob `agent_pdf_read_cache_max_entries` (Settings + snapshot + PATCH allowlist).
- **Policy:** `EXTERNAL_RESEARCH_WEB_TOOL_NAMES` vs `read_external_pdf`; explicit `pdf_read_request` bypasses web-research denylist for PDF only; `pdf_reading_mode=off` blocks agent PDF unless explicit request; LLM `allowed_domains` / `blocked_domains` on the tool are ignored (server policy).
- **Evidence:** PDF success uses `evidence_quality=variable`; failed `read_external_pdf` hydrates citations like `web_fetch` / `unpaywall` failures.
- **UI:** Native token + i18n user-turn label; pdf-only submit; product-step strings for PDF prefetch.
- **Transport:** `run_metadata` includes `pdf_read_artifact_id`, `pdf_read_tool_ok` / `pdf_read_tool_error`, and cache/durable hit flags when present; SSE `product_step` `pdf_read_extracting` echoes the same compact fields after server-side prefetch. Session sync keeps `pdf_read_*` keys via `compactAskTurnDetailsForSync`.
- **Durable cache (optional):** Redis JSON metadata keyed by URL hash + budget fingerprint when `agent_pdf_read_durable_cache_enabled` is on and Redis URL is configured; enables cold-start reuse without rewriting `execute_pdf_read` core.
- **Live matrix:** Operator checklist in `scripts/live_check/pdf_read_live_matrix.md` (after `make dev-up` + `config-check`).

**Residual:** Postgres/object-store artifact rows for audit and large-byte retention — see `docs/backlog/refactor-backend.md` → `[PARTIAL] Durable PDF read artifacts`.

