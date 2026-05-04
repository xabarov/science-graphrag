# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Completed (archive)

Summaries only; specs and ADRs hold detail (`graph-ui-plan`, `frontend-ui-api-contracts`, ADR 006/007, ingestion roadmap).

| When | Theme |
|------|--------|
| 2026-04-25 | **Graph:** `GraphCanvasMvp` split (`useGraphCanvasInput`, `graphCanvasDraw`); aggregator rendering + expand; `GraphWorkspacePanel` split (`useGraphWorkspaceData`, side panel, mode switch, debug inspector). |
| 2026-04-25 | **Ask:** `AskPanel` → `useAskSubmit`, `AskSessionControls`, `AskAnswerPanel` (composition shell). |
| 2026-04-25 | **Ingest UI:** `IngestStageStepper` + `useJobStream` (SSE) + polling fallback in workspace ingest. |
| 2026-04-24 | **Workspaces / workspace:** Wave I — `WorkspacesPage` shell + panels; `WorkspacePage` shell + ingest / dedup / paper list extraction. |
| 2026-04-08 | **Graph standalone:** Waves 5–8 (maximize canvas, graph page query helpers / focus / detail width, drag gutter, contract + pointer-capture polish). |
| 2026-04-08 | **Graph canvas:** Wave 4.2 z-order; Wave 4.3 React Flow mode; Canvas force layout + quadTree/communities (ADR 007). |
| 2026-04-08 | **API errors:** unified `formatResearchApiError` in `researchApi.js` + tests. |
| 2026-04-26 | **Graph:** Bloom-like overview — type counts + node/edge totals in legend, chip sort frequency/alphabet, canvas edge-label modes (`all` / `interaction` / `adaptive`) + `GraphCanvasViewToolbar`, local node substring search (`graphNodeSearch.js`, `GraphWorkspacePanel`). |
| 2026-04-26 | **Research API (UI):** `services/research/{errors,meta,queryModel,queryHttp,askSessions,agent,ideaAssist,works,graph}.js` + barrel `researchApi.js`; shim `benchmarkSummary.js` removed (`useBenchmarkSummary` → `benchmarkApi.js`). |
| 2026-04-26 | **Benchmark UI:** Compare/Run tabs split — `useCompareTab`, `CompareDeltaTable`, `CompareTabSummarySection`, `benchmarkCompareModel` + vitest; `useRunTab`, `RunTabCurrentRunSection`, `runTabCaseToggle`; workbench run panel → `workbench/BenchmarkWorkbenchRunPanel.jsx` (`WorkbenchRunScopedPanel`). |
| 2026-04-26 | **Workspace UX + ingest dedup (full-stack slice):** full-width `WorkspacePage`; `PageActionToolbar` / `CursorIconAction` / `CopyIdButton` in hero and cards; side panel без smart-dedup poll; удалены `WorkspaceDedupSection`, `DeduplicationPanel`, `WorkDedupReviewDialog`; `IngestConflictReviewCard` + `pending_conflicts_count` на ingest job; икон-действия на Home / Workspaces / Graph / Benchmark / Settings / Diagnostics / Admin entry / NotFound / workspace tabs. *(Пункт drawer «Evidence» убран 2026-04-27 — см. `buildStandaloneEvidencePath`, `/evidence`.)* |
| 2026-04-27 | **Evidence IA (navigation + traceability):** убран primary пункт `/evidence` из `Drawer.jsx`; канонические ссылки `buildStandaloneEvidencePath`; удалены неиспользуемые `WorkspacePage/tabs/{Overview,Graph,Evidence}Tab.jsx`; `WORKSPACE_TAB_SLUGS` без `evidence`; i18n + `route-map` / master-plan синхронизированы. |
| 2026-04-26 | **Big plan slice (UI / wiring):** `paths.py` import в aggregator; child batch `progress_pct` в `WorkspaceIngestPanel.jsx`; `WorkspaceLayout` / `WorkspaceContextChip`; i18n `settings.ingestion.saveError`; `.env.example` → ADR-021; SSE `/v2/agent/query` (`useAgentStream` + `useAskSubmit`). Backend-only (`EDGE_DISPLAY_TYPE_READER`, dual_validate glue) — см. [`refactor-backend.md`](./refactor-backend.md) Completed. |
| 2026-04-26 | **Former `[DONE]` queue (graph):** double-click fit selection (`graphCanvasCamera`); GR6 canvas uses `displayType`; GR7 `graphLocalize` EN/RU. |
| 2026-04-26 | **Former `[DONE]` queue (benchmark / workspace / reader):** TrustSignalDrillIn; `CaseDetailDialog` → `caseDetail/*` + families registry; slim `WorkspacePage`; `ReaderWorkBody` split; WX1 layout/hero/side panel; WX3 ingest conflicts card; WX4 `PageActionToolbar` / `CursorIconAction`; WX6 smart-dedup surface removal; EF-Cards / EF-Evidence / Reader RX1 + single-column cleanup; `useScienceGraphForceSimulation` → `hooks/graph/`; `Cursor*` on `IngestConflictReviewCard`. |
| 2026-04-27 | **WX5 minimal + shell polish:** [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) (re-export chip) в [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx) и [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx); i18n `workspace.hero.switchWorkspaceHint` (EN/RU); chip label без UUID — `shell.workspaceChip.unnamed` когда нет имени ([`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx)); `WorkspaceLayout` — больший `minHeight` grid + flex main. |
| 2026-04-27 | **WX5 empty-state CTA:** кнопка «Новая область» / `workspace.empty.createWorkspace` + `createWorkspace()` и синхрон URL `workspace_id` в [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) empty-state; i18n EN/RU в `partWorkspacePage.js`. |
| 2026-04-27 | **Graph GR-UX1 — command bar:** единая панель [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx) — `GraphScopeMenu` / меню узлов / `GraphViewChips` в `toolbar/` (исторически глубина `1°/2°` и `GraphNodeTypesMenu`; **2026-04-27:** глубина workspace убрана, типы — клиентский `GraphNodesVisibilityMenu` + `graphVisibilityFilter`); тултипы stats, локальный поиск + чипы «Детали / Легенда / Диагностика»; [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx) — `Collapse` легенды + `graphEmbeddedLegendOpen`; [`GraphTypeLegend.jsx`](../../ui/src/components/graph/shell/GraphTypeLegend.jsx) — компактный header; i18n `partGraphUi` EN+RU; vitest [`WorkspaceGraphToolbar.test.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.test.jsx). |
| 2026-04-27 | **Workspace graph — full 1-hop:** сервер всегда отдаёт полную 1-hop окрестность по всем работам в workspace (`build_from_depth1_rows`, без `depth`/`neighbor_limit`/`node_types` в query); neighbors/expand без лимитов; фронт только фильтрует видимость; pytest + vitest обновлены; ADR 011/012 addendum + `graph-ui-plan` + root-cause analysis. |
| 2026-04-27 | **LT1 appearance foundation:** `ui/src/theme/` — `appearanceMode.js`, `buildAppTheme.js` (`appTokens`), `AppearanceProvider.jsx`, inline first-paint в [`ui/index.html`](../../ui/index.html), [`main.jsx`](../../ui/src/main.jsx) без inline `createTheme`; [`styles.css`](../../ui/src/styles.css) по `html[data-color-scheme]`; [`GeneralSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/GeneralSettingsPanel.jsx) + i18n `partSettings` EN/RU; vitest [`appearanceMode.test.js`](../../ui/src/theme/appearanceMode.test.js). Контракт: [`light-theme-roadmap-2026-04-27.md`](../../docs/analysis/light-theme-roadmap-2026-04-27.md) §10. |
| 2026-04-27 | **Ask:** `AskPanel` → [`useAskPanelOrchestration.js`](../../ui/src/components/work/ask/useAskPanelOrchestration.js) + [`AskPanelChrome.jsx`](../../ui/src/components/work/ask/AskPanelChrome.jsx); shell-only [`AskPanel.jsx`](../../ui/src/components/work/ask/AskPanel.jsx). |
| 2026-04-26 | **Graph standalone — scope bugfix:** кнопка «Граф» на [`WorkPaperCard`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx) ведёт на `/graph?work_id=…` без `workspace_id`; [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) больше не подставляет `activeWorkspaceId` в этом случае — иначе [`useGraphWorkspaceData`](../../ui/src/components/graph/workspace/hooks/useGraphWorkspaceData.js) грузил полный workspace graph и игнорировал работу. |
| 2026-04-28 | **Graph scope regression (workspace paper row):** кратковременно [`WorkspacePaperRow.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperRow.jsx) передавал `workspace_id` в `workGraphUrl` → URL с обоими query-параметрами → `getWorkspaceGraph` и **весь** workspace на графе статьи. Возврат к **`workGraphUrl(workId, null)`**; см. [`work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md) §7 Phase 2 product link (revised). |
| 2026-04-28 | **Graph navigation Phase 2 (IA):** [`paths.js`](../../ui/src/routes/paths.js) `READER_PATH`/`GRAPH_PATH`; tool links use `buildStandaloneTracePath` (Evidence/Reader/Graph pages, `EvidenceWorkBody`, `AskAnswerPanel`, `ReaderTab`); [`legacyWorkspaceTabRedirectTarget`](../../ui/src/components/work/traceability/traceabilityState.js) + replace redirect in [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) for legacy `/workspace?tab=reader|graph|ask`; removed unused `persistWorkspaceTab` / `LAST_WORK_TAB_KEY`; vitest updated. Remediation: [`graph-navigation-hash-router-remediation-plan-2026-04-28.md`](../analysis/graph-navigation-hash-router-remediation-plan-2026-04-28.md) Phase 2. |
| 2026-04-28 | **Graph navigation Phase 3:** [`ui/src/routing/`](../../ui/src/routing/) — `queryKeys.js`, `graphPageQuery.js` (ex-`graphPageUrl`), barrel [`index.js`](../../ui/src/routing/index.js); [`paths.js`](../../ui/src/routes/paths.js) `WORKSPACE_PATH` / `EVIDENCE_PATH`; [`workspacePageUrls.js`](../../ui/src/pages/WorkspacePage/workspacePageUrls.js) delegates to traceability builders; vitest [`workspacePageUrls.test.js`](../../ui/src/pages/WorkspacePage/workspacePageUrls.test.js), [`graphPageQuery.test.js`](../../ui/src/routing/graphPageQuery.test.js). Remediation Phase 3. |
| 2026-04-28 | **Graph navigation Phase 4:** vitest shell smoke [`graphNavigationDashboardShell.test.jsx`](../../ui/src/graphNavigationDashboardShell.test.jsx) — real `DashboardLayout` + drawer from `/graph` stub after `setSearchParams`; `history.back()` preserves selection query (`replace` contract). Remediation Phase 4; manual QA checklist remains in [`graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx) header for full canvas/prod URL shape. |
| 2026-04-29 | **Graph folder layout:** `ui/src/components/graph/` split into `canvas/` (MVP + canvas hooks + `canvas/physics/`), `flow/`, `workspace/`, `shell/`, `model/` (adapters, view state, limits, telemetry, localize); cross-imports and `docs/` path references updated; `toolbar/` and `hooks/useGraphSelectionReconcile.js` unchanged. |
| 2026-04-29 | **Work UI layout:** `ui/src/components/work/` split into `traceability/`, `shared/`, `markdown/`, `agent/`, `reader/`, `ask/`, `evidence/`, `hypothesis/`; pages + `routing/index.js` + graph imports updated; vitest + ESLint green. |
| 2026-05-04 | **Backlog audit:** `components/work/` and `components/graph/` match the layout above; remaining hotspots are oversized leaf modules (see Queue — P1 module splits) and product UX items below. `WorkspaceContextChip` already includes searchable workspace list (filter by name/id); earlier backlog text implying «no search» was stale. |
| 2026-05-05 | **Backlog code verification:** Queue P1 LOC counts match `wc -l` on current tree (`GraphDetailPanel` 895, `LlmSettingsPanel` 737, `StorageSettingsPanel` 615, `useWorkspacePageCore` 550, `ChatMessageThread` 544, `GraphCanvasMvp` 499, `WorkspaceContextChip` 449). `POST /v1/agent/query` is still called from [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) (`handleSummarizeWorkspace`). Non-streaming ask in [`useAskSubmit.js`](../../ui/src/components/work/ask/useAskSubmit.js) uses **`postAgentQueryV2`** (`/v2/agent/query`), not v1. [`ui/src/api/agent.js`](../../ui/src/api/agent.js) re-exports v1 and has **no** in-repo imports — dead shim candidate. |

## Queue

Closed items live only in **Completed (archive)** above (no `### [DONE]` bodies here).

Priorities: **P0** = user-visible risk or scaling ceiling; **P1** = maintainability / files over ~400 LOC or tangled hooks; **P2** = polish and optional depth.

Backend-only follow-ups (dedup HTTP removal, Agent V2 locale) live in [`refactor-backend.md`](./refactor-backend.md); do not track duplicate narratives here.

---

### P0 — Scaling and reliability

#### [OPEN] Workspace graph — canvas perf for very large payloads (10k+ edges)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx), [`GraphFlowView.jsx`](../../ui/src/components/graph/flow/GraphFlowView.jsx), [`graphUiLimits.js`](../../ui/src/components/graph/model/graphUiLimits.js), optional virtualization / level-of-detail
- **Issue:** Workspace graph API can return the full 1-hop union; dense workspaces stress layout + draw; `capGraphForUi` caps display but parse/normalization still grow with payload.
- **Proposal:** Profile a high–edge-count workspace snapshot; progressive disclosure, Web Worker normalization, or server subset if product requires.
- **Acceptance:** Documented threshold + measured interaction budget on a reference workspace; no silent tab freeze on load.
- **Raised:** 2026-04-27

#### [OPEN] Graph canvas — physics vs pointer policy (follow-up)
- **Area:** [`ui/src/hooks/graph/useGraphPhysicsPolicy.js`](../../ui/src/hooks/graph/useGraphPhysicsPolicy.js), [`useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js), [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx), [`GraphPhysicsPointerBridgeContext.jsx`](../../ui/src/components/graph/canvas/GraphPhysicsPointerBridgeContext.jsx), [`useGraphCanvasViewport.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasViewport.js)
- **Issue:** Pause reasons for force simulation were historically split across rAF, window events, and hit-test timing; easy to regress clicks or drawer navigation when changing the integrator.
- **Proposal:** Extend vitest when adding new pause sources (e.g. modals); consider splitting `GraphCanvasMvp` further (draw loop vs chrome) if it grows again.
- **Acceptance:** Integration-pause reasons flow through `useGraphPhysicsPolicy` (or documented successor); vitest covers pointer session vs `integrationBlocked`; shell + canvas smoke stay green.
- **Raised:** 2026-04-29

---

### P1 — Module size and coupling

#### [OPEN] Graph shell — split `GraphDetailPanel`
- **Area:** [`ui/src/components/graph/shell/GraphDetailPanel.jsx`](../../ui/src/components/graph/shell/GraphDetailPanel.jsx) (~895 LOC)
- **Issue:** Single file holds claim/aggregator/work formatting, accordions, and markdown previews — hard to test and risky to change.
- **Proposal:** Extract claim block, work/entity sections, and property formatters into `shell/detail/` (or `model/` + presentational components); keep `graphLocalize` usage centralized.
- **Acceptance:** No single file in that subtree > ~400 LOC without team agreement; vitest/graph smoke green.
- **Raised:** 2026-05-04

#### [OPEN] Settings — split LLM and storage panels
- **Area:** [`LlmSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/LlmSettingsPanel.jsx) (~737 LOC), [`StorageSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/StorageSettingsPanel.jsx) (~615 LOC)
- **Issue:** Large single components mix sections (providers, keys, advanced toggles, diagnostics).
- **Proposal:** Section components + shared settings row primitives (reuse `settingsFormSx` patterns).
- **Acceptance:** Same UX; `npm run lint` / focused tests green; main panels stay thin orchestrators.
- **Raised:** 2026-05-04

#### [OPEN] Workspace page — thin `useWorkspacePageCore` + related wiring
- **Area:** [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) (~550 LOC), consumers in [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** Core hook mixes load effects, ingest/dedup coordination, tab routing, and empty-state flows.
- **Proposal:** Extract `useWorkspaceLoad`, `useWorkspaceIngestBridge`, or similar; document public surface.
- **Acceptance:** Hook responsibilities one screen-width summary each; no behavioral change.
- **Raised:** 2026-05-04

#### [OPEN] Ask UI — split `ChatMessageThread`
- **Area:** [`ui/src/components/work/ask/ChatMessageThread.jsx`](../../ui/src/components/work/ask/ChatMessageThread.jsx) (~544 LOC)
- **Issue:** Thread rendering, grouping, and tool blocks in one component complicate ask-feature work.
- **Proposal:** Extract message group row, tool-call rendering, and empty/loading states.
- **Acceptance:** Component tests still pass; optional story-sized subcomponents.
- **Raised:** 2026-05-04

#### [OPEN] Workspaces landing — split `WorkspacesPage` / `WorkspaceContextStrip`
- **Area:** [`WorkspacesPage.jsx`](../../ui/src/pages/WorkspacesPage.jsx) (~428 LOC), [`WorkspaceContextStrip.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceContextStrip.jsx) (~411 LOC)
- **Issue:** Page-level shells combine layout, hero/actions, and list/browser regions in few files (above typical ~400 LOC page budget).
- **Proposal:** Align with existing [`pages/WorkspacesPage/`](../../ui/src/pages/WorkspacesPage/) subfolder — extract strips, panels, and empty states; mirror patterns from `WorkspacePage/`.
- **Acceptance:** Smaller top-level page files; behavior unchanged; `npm run lint` / smoke tests green.
- **Raised:** 2026-05-05

#### [OPEN] Graph reader DRY — slim `authorSemanticProjection` after server parity
- **Area:** [`authorSemanticProjection.js`](../../ui/src/components/graph/model/authorSemanticProjection.js), [`useGraphWorkspaceData.js`](../../ui/src/components/graph/workspace/hooks/useGraphWorkspaceData.js), graph visibility / external-work filters
- **Issue:** Client mirrors server reader authorship semantics; risks drift vs `collapse_authorship_for_reader_view`.
- **Proposal:** After backend phases in [`docs/analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](../analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md), delete redundant projection branches; optional `workspace_id` on work graph for membership filters when API supports it.
- **Acceptance:** `authorSemanticProjection.js` documented as presentation-only or removed; vitest/graph smoke green.
- **Raised:** 2026-04-28

#### [OPEN] useAgentStream — abort reason taxonomy
- **Progress (2026-04-27):** callbacks stabilized via `useRef` + `useEffect`; `stream` stable when callback identities change. **Remaining:** distinguish `AbortError` causes (navigation vs new submit) for consumers.
- **Area:** [`ui/src/hooks/useAgentStream.js`](../../ui/src/hooks/useAgentStream.js)
- **Proposal:** Optional `abortReason` or suppress `onError` on expected user abort; document contract in hook header; unit test for abort vs fatal error.
- **Acceptance:** Test covers abort path; no spurious «stream ended without final answer» on intentional cancel.
- **Raised:** 2026-04-27

#### [OPEN] Agent query — deprecate `POST /v1/agent/query` (Wave Y6)
- **Area:** [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) (`handleSummarizeWorkspace` → [`postAgentQuery`](../../ui/src/services/research/agent.js)), [`research/agent.js`](../../ui/src/services/research/agent.js), optional delete of unused [`ui/src/api/agent.js`](../../ui/src/api/agent.js); `science_graphrag/api` routes
- **Issue:** Chat/streaming uses `/v2/agent/query`; **v1 remains** for workspace summary (sync JSON). [`useAskSubmit`](../../ui/src/components/work/ask/useAskSubmit.js) non-streaming path already calls **`postAgentQueryV2`**, not v1. The `api/agent.js` shim re-exports v1 and appears unused in-repo.
- **Proposal:** Migrate `handleSummarizeWorkspace` to `postAgentQueryV2` (sync) or a dedicated summary endpoint; remove `api/agent.js` after grep confirms no consumers; then retire `/v1/agent/query` on the server when safe.
- **Acceptance:** Summary + ask flows work; OpenAPI/tests/docs updated; v1 callsites gone from `ui/`.
- **Raised:** 2026-04-27; **updated:** 2026-05-05 (callsite audit)

---

### P2 — Product UX and polish

#### [OPEN] Benchmark panel — experiment-centric product surface
- **Area:** `ui/src/pages/BenchmarkPage/`, `ui/src/services/benchmarkApi.js`
- **Issue:** Surface mixes launcher, trust, history, compare, cases, workbench — harder to read as experiment → variant → analysis.
- **Proposal:** See `docs/analysis/benchmark-panel-research-redesign-plan-2026-04-27.md`; optional backend run-group API; API-normalized scorecards (redesign doc §9.4).
- **Acceptance:** Launch/compare/read metrics without trust-first navigation friction.
- **Progress (2026-04-28):** Analysis defaults, Run Lab, More tools — **still open:** run-group API, scorecard normalization, split `useRunTab` if it grows.
- **Raised:** 2026-04-27

#### [OPEN] Workspace shell — layout affordance and chip decomposition
- **Area:** [`DashboardLayout`](../../ui/src/components/layout/DashboardLayout/), [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (~449 LOC), [`WorkspaceLayout.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceLayout.jsx)
- **Issue:** Popover search/sort **exist**; chip trigger still dense (id tooltip + long row list); main column can feel empty below the card grid on large viewports.
- **Proposal:** (1) Extract list/popover from `WorkspaceContextChip` into `WorkspaceSwitcher` subcomponents (reduce file size, clarify props). (2) Optional second-row content or flex-fill so ingest/conflict cards anchor the column when active.
- **Acceptance:** Before/after screenshots at 1440×900; `npm run lint` green.
- **Raised:** 2026-04-26; **updated:** 2026-05-04 (removed stale «no search» claim)

#### [OPEN] Ingest job UI — polish (post–`IngestProgressCard`)
- **Area:** [`IngestProgressCard.jsx`](../../ui/src/components/ingestion/IngestProgressCard.jsx), [`IngestStageRow.jsx`](../../ui/src/components/ingestion/IngestStageRow.jsx), [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx), i18n `partWorkspacePage`
- **Issue:** Card + determinate progress + stage rows **shipped**; stage **names** still often raw backend keys (`vl_extract`, …) unless mapped; optional shimmer / aggregate ETA from remaining `expected_duration_ms` per [`workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.2.
- **Proposal:** `t("workspace.ingest.stage.<key>")` registry with fallback to raw; optional active-stage shimmer; ETA line when backend sends durations (WX2-BE synergy).
- **Acceptance:** RU locale shows human-readable stage labels for known keys; logs stay under Details accordion.
- **Raised:** 2026-04-25; **updated:** 2026-05-04 (merged former WX2-FE / WX4 follow-ups into this single item)

#### [OPEN] Ingest conflict UI — osint-grade resolver (entity types + inline job)
- **Area:** [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx), [`EntityConflictReviewCard.jsx`](../../ui/src/components/dedup/EntityConflictReviewCard.jsx) (both mounted from [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)), [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx), ingest job types
- **Issue:** Cards cover work/entity pair flows; no full osint-style `ConflictResolver` branching; limited coupling to active ingest stream.
- **Proposal:** After backend parity (see backend backlog): unified conflict model; optional drawer during job. Reference: `osint-gr` ConflictResolver UX.
- **Acceptance:** Component or e2e on state transitions; i18n for new fields.
- **Raised:** 2026-04-26

#### [OPEN] Graph canvas — Neo4j Browser–grade UX (optional)
- **Area:** `GraphCanvasMvp.jsx` / hooks
- **Proposal:** Small PRs: (1) node context menu — Fit / Center / Copy id; (2) compact edge-type legend on canvas aligned with `GraphTypeLegend`.
- **Acceptance:** Per item; `npm run lint` / `npm run test` in `ui/`.
- **Raised:** 2026-04-26

#### [OPEN] Wave EF-Reader — RX2 reading affordances (TOC, language banner, copy-id)
- **Area:** [`ReaderWorkDetailCard.jsx`](../../ui/src/components/work/reader/ReaderWorkDetailCard.jsx), [`ReaderPage.jsx`](../../ui/src/pages/ReaderPage.jsx), [`ReaderTab.jsx`](../../ui/src/pages/WorkspacePage/tabs/ReaderTab.jsx)
- **Issue:** TOC, language banner, copy `work_id` — see [`reader-ux-and-translation-roadmap-2026-04-25.md`](../analysis/reader-ux-and-translation-roadmap-2026-04-25.md) §1.4–§1.6.
- **Proposal:** `ReaderToc` from `section_path`; shared layout between standalone reader and workspace tab.
- **Acceptance:** Lint/test/build green; laptop layout without horizontal scroll.
- **Raised:** 2026-04-26

#### [OPEN] i18n — residual hardcoded copy audit
- **Area:** spot-check [`HypothesisPanel.jsx`](../../ui/src/components/work/hypothesis/HypothesisPanel.jsx), [`IngestionSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx), dialogs under `WorkspacePage/`; **confirmed EN-only:** workspace summary prompt string inside [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) (`handleSummarizeWorkspace`, passed to `postAgentQuery`)
- **Issue:** Prior passes fixed many literals; occasional EN-only strings may remain.
- **Proposal:** Grep + align with [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md); localize summary prompt or derive from `t()` when touching Y6 migration above.
- **Acceptance:** No user-visible literals in scoped files; `npm run lint` green.
- **Raised:** 2026-04-25; **updated:** 2026-05-05 (summarize prompt called out)
