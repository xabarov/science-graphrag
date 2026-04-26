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
| 2026-04-08 | **Graph standalone:** Waves 5–8 (maximize canvas, `graphPageUrl` / focus / detail width, drag gutter, contract + pointer-capture polish). |
| 2026-04-08 | **Graph canvas:** Wave 4.2 z-order; Wave 4.3 React Flow mode; Canvas force layout + quadTree/communities (ADR 007). |
| 2026-04-08 | **API errors:** unified `formatResearchApiError` in `researchApi.js` + tests. |
| 2026-04-26 | **Graph:** Bloom-like overview — type counts + node/edge totals in legend, chip sort frequency/alphabet, canvas edge-label modes (`all` / `interaction` / `adaptive`) + `GraphCanvasViewToolbar`, local node substring search (`graphNodeSearch.js`, `GraphWorkspacePanel`). |
| 2026-04-26 | **Research API (UI):** `services/research/{errors,meta,queryModel,queryHttp,askSessions,agent,ideaAssist,works,graph}.js` + barrel `researchApi.js`; shim `benchmarkSummary.js` removed (`useBenchmarkSummary` → `benchmarkApi.js`). |
| 2026-04-26 | **Benchmark UI:** Compare/Run tabs split — `useCompareTab`, `CompareDeltaTable`, `CompareTabSummarySection`, `benchmarkCompareModel` + vitest; `useRunTab`, `RunTabCurrentRunSection`, `runTabCaseToggle`; workbench run panel → `workbench/BenchmarkWorkbenchRunPanel.jsx` (`WorkbenchRunScopedPanel`). |

## Queue

### [DONE] Graph canvas — Neo4j Browser–grade UX (slice: double-click fit selection)
- **Note (2026-04-26):** `graphCanvasCamera.js` (`buildPositionSubset`, `computeFitTransformForNodeSubset`) + `graphCanvasCamera.test.js`; `GraphCanvasMvp.jsx` — `onDoubleClick` на canvas вписывает вид в bbox текущего `selectedNodeId` (как full fit, с тем же `NODE_RADIUS` / padding / `MIN_FIT_SCALE`). i18n: `graph.canvas.helpTooltip`, `helpAria`, `regionAria` (EN+RU). Мультивыделение — когда появится на уровне workspace, прокинуть iterable id в тот же helper.
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`graphCanvasCamera.js`](../../ui/src/components/graph/graphCanvasCamera.js), [`partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js) (EN+RU)
- **Raised:** 2026-04-08; closed slice 2026-04-26

### [OPEN] Graph canvas — Neo4j Browser–grade UX (optional follow-ups)
- **Area:** `GraphCanvasMvp.jsx` / рядом hooks
- **Issue:** В Neo4j Browser ещё есть command bar, стили рёбер по типу, инспектор запросов, контекстное меню, экспорт — не требуются для read-only neighborhood v1.
- **Proposal:** Отдельными маленькими PR: (1) контекстное меню узла (ПКМ): минимум Fit / Center / Copy id; (2) компактная легенда типов рёбер на canvas, согласованная с `GraphTypeLegend`, без поломки режимов подписей рёбер.
- **Acceptance:** по пункту; `npm run lint` / `npm run test` в `ui/`.
- **Raised:** 2026-04-26

### [DONE] Graph UI — Neo4j Bloom–inspired overview (counts, edge labels, local find)
- **Note (2026-04-26):** Счётчики по `nodeKind` / типу рёбер + строка «узлов / рёбер», сортировка чипов frequency vs alphabet (`graphTypeLegend.js`, `GraphTypeLegend.jsx`). Подписи рёбер на canvas: режимы `all` \| `interaction` \| `adaptive`, `shouldDrawCanvasEdgeLabel` + константы в `graphCanvasDraw.js`, persist режима в `localStorage`, i18n `graph.canvas.edgeLabels.*`, тулбар `GraphCanvasViewToolbar.jsx`. Локальный поиск: `graphNodeSearch.js`, интеграция в `GraphWorkspacePanel.jsx`. Тесты: `graphTypeLegend.test.js`, `graphCanvasDraw.test.js`, `graphNodeSearch.test.js`. `GraphCanvasMvp.jsx` остаётся крупным — опциональный follow-up slim.
- **Area:** [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx),
  [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx),
  [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`graphCanvasDraw.js`](../../ui/src/components/graph/graphCanvasDraw.js),
  [`GraphCanvasViewToolbar.jsx`](../../ui/src/components/graph/GraphCanvasViewToolbar.jsx), [`graphNodeSearch.js`](../../ui/src/components/graph/graphNodeSearch.js),
  [`partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js) (EN+RU)
- **Raised:** 2026-04-26 (обсуждение UI vs Neo4j Bloom/Browser)

### [DONE] Graph UI — Wave GR6 use displayType on canvas (closes Wave GR2 frontend gap)
- **Note (2026-04-26):** `edgeTypeCanvasLabelFromEdge` + opts on `edgeTypeCanvasLabel`; canvas + React Flow labels aligned; tests in `graphCanvasStyle.test.js` / `graphFlowAdapter.test.js`.
- **Area:** [`graphCanvasDraw.js`](../../ui/src/components/graph/graphCanvasDraw.js),
  [`graphCanvasStyle.js`](../../ui/src/components/graph/graphCanvasStyle.js),
  [`graphFlowAdapter.js`](../../ui/src/components/graph/graphFlowAdapter.js),
  [`graphCanvasStyle.test.js`](../../ui/src/components/graph/graphCanvasStyle.test.js),
  [`graphFlowAdapter.test.js`](../../ui/src/components/graph/graphFlowAdapter.test.js)
- **Issue:** Канвас рисует raw `edge.type` (`HAS_AUTHORSHIP`, `OF_AUTHOR`, `CITES`), игнорируя
  `edge.displayType`, который backend GR2 уже возвращает. Боковая панель и React Flow адаптер
  используют `displayType` корректно — на канвасе видны технические Neo4j-метки.
- **Proposal:** В `drawLabels` (line 112) заменить `edgeTypeCanvasLabel(edge.type)` на
  `edgeTypeCanvasLabel(edge.displayType || edge.type)`; обновить `edgeTypeCanvasLabel` так,
  чтобы пустой fallback заменял `_` на пробел; добавить unit-тест на displayType-кейс.
- **Acceptance:** на канвасе `/graph?work_id=…` рёбра подписаны как `cites`, `is author of`,
  `affiliated with`; `npm run lint` / `npm run test` зелёные.
- **Synergy:** **Wave GR2** backend done; этот пункт закрывает frontend integration. Делается
  отдельным микро-PR, до Wave GR7 (i18n).
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.1)

### [DONE] Graph UI — Wave GR7 i18n EN/RU for graph edges, node kinds, aggregator labels
- **Note (2026-04-26):** `graphLocalize.js` (`localizeEdgeType`, `localizeNodeKind`, `localizeAggregatorTitle`, …);
  keys in `partGraphUi` EN/RU (`graph.edgeType.*`, `graph.nodeKind.*`, `graph.aggregator.*`, `graph.legend.*`, `graph.detailPanel.*`);
  canvas `drawLabels` + `GraphCanvasMvp` resolvers; `buildReactFlowEdges` options + `GraphFlowView`; `GraphDetailPanel`, `GraphTypeLegend`.
  Tests: `graphLocalize.test.js`, `graphFlowAdapter.test.js`, `graphTypeLegend.test.js` (I18nProvider). `npm run lint` / `npm run test` green.
- **Area:** [`ui/src/i18n/messages/en/partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js),
  [`ui/src/i18n/messages/ru/partGraphUi.js`](../../ui/src/i18n/messages/ru/partGraphUi.js),
  [`ui/src/components/graph/graphLocalize.js`](../../ui/src/components/graph/graphLocalize.js),
  [`graphCanvasDraw.js`](../../ui/src/components/graph/graphCanvasDraw.js),
  [`graphFlowAdapter.js`](../../ui/src/components/graph/graphFlowAdapter.js),
  [`GraphDetailPanel.jsx`](../../ui/src/components/graph/GraphDetailPanel.jsx),
  [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx)
- **Issue:** `display_type` приходит EN-строкой из backend (`graph_display.py:EDGE_DISPLAY_TYPE_RAW`),
  поэтому русская локаль показывает «authored by» / «is author of» вместо «является автором» /
  «цитирует». То же — для `node_kind` и подписей агрегаторов («8 author of Work»).
- **Proposal:** Локализация по raw key (`edge.type`) через `t("graph.edgeType.HAS_AUTHORSHIP")`;
  единый модуль `graphLocalize.js` с `localizeEdgeType(edge, t)`,
  `localizeNodeKind(node, t)`, `localizeAggregatorLabel(node, t)`; ключи добавить в
  `partGraphUi.js` обоих локалей; функцию `t` пробросить из `<GraphCanvasMvp>` в `drawLabels`.
- **Acceptance:** на ru-локали ребра «цитирует»/«использует метод»/«опубликовано в»; узлы-агрегаторы
  «5 авторов работы»; EN regression-safe; `npm run lint` зелёный.
- **Synergy:** Закрывает второй пункт из жалобы пользователя («не поддерживает перевод на русский»).
  Опциональная фаза B (backend `display_*_key` поля) — отдельный backend-пункт в
  [`refactor-backend.md`](./refactor-backend.md).
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.2)

### [DONE] Drop `ui/src/services/research/benchmarkSummary.js` shim
- **Note (2026-04-26):** Файл shim удалён; [`useBenchmarkSummary.js`](../../ui/src/hooks/useBenchmarkSummary.js) вызывает [`fetchDecisionGateSummary`](../../ui/src/services/benchmarkApi.js) из `services/benchmarkApi.js`.

### [DONE] Benchmark trust drill-in (`TrustSignalPanel` + API slice)
- **Note (2026-04-26):** `TrustSignalDrillIn.jsx` + `trustSignalDrillInHelpers.js` + list/table subcomponents; i18n `benchmarkPage.trustDrillIn.*` + `benchmarkPage.trustSignal.toggleDetailsAria` EN/RU; vitest для хелперов и drill-in.
- **Area:** [`TrustSignalPanel.jsx`](../../ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx), [`benchmark_decision_gate.py`](../../science_graphrag/api/benchmark_decision_gate.py) (optional: extend response), i18n `partBenchmarkPage.js`.
- **Issue:** API already returns `trust_signal.consistency_warnings`, `validation_status_aggregate`, and `criteria.advisory_individual_failures`; UI only shows decision chip + `runtime_mode` rows — operators cannot drill into failed case_ids without opening raw JSON.
- **Proposal:** Expandable rows or secondary panel: show `consistency_warnings`, `validation_status_aggregate`, and a compact table for `criteria.advisory_individual_failures` (case_id, family.member); extract presentational helpers to `TrustSignalDrillIn.jsx` when file approaches ~250 lines.
- **Acceptance:** `/benchmark` shows actionable drill-in for judge failures and phantom warnings; `npm run lint` / vitest green.
- **Synergy:** **Round 6 BT2–BT5** — more fields in summary; avoid growing `TrustSignalPanel.jsx` into a god-component.
- **Raised:** 2026-04-26 (post-BT1).

### [DONE] Split `BenchmarkPage/CaseDetailDialog.jsx` (790)
- **Area:** [`BenchmarkPage/CaseDetailDialog.jsx`](../../ui/src/pages/BenchmarkPage/CaseDetailDialog.jsx), смежные `BenchmarkPage/{CompareTab,RunTab,BenchmarkWorkbenchTab,BenchmarkRunCasesTable}.jsx`
- **Issue:** Один диалог с превью кейса, таблицами gold vs pred, server preview, ошибками; работает в трёх вкладках. С добавлением новых семейств (`workspace_scoped`, `hybrid_ablation`, `multihop`, `agent_tools`, `idea_assist`) растёт линейно.
- **Proposal:** Вынести `CasePreviewTable`, `GoldVsPredSection`, `useCaseDetailDialogData` (fetch + ошибки + кеш). Семейство-специфичные превью — в `pages/BenchmarkPage/families/<family>.jsx`.
- **Acceptance:** ни один файл в `pages/BenchmarkPage/` не превышает ~400 строк; добавление нового семейства бенчмарков требует только нового `families/<name>.jsx` + регистрации.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap` — постоянно добавляются семейства бенчмарков.
- **Raised:** 2026-04-25
- **Done note (2026-04-26):** split into `caseDetail/*` (hooks + sections + graph subpanels), `families/registry.js` + `default|layer1|graph`, i18n `partBenchmarkCaseDialog` (EN+RU); shell `CaseDetailDialog.jsx` ~110 lines. Лимит ~400 строк по дереву `BenchmarkPage/` закрыт совместно с пунктом Compare/Run + workbench panel (см. строку в Completed и `[DONE]` Compare/Run ниже).

### [DONE] Slim `WorkspacePage.jsx` (530) — extract papers model + dialogs + ingest wiring
- **Note (2026-04-26):** `useWorkspacePapersModel.js`, `useWorkspacePageCore.js`, `WorkspaceDialogs.jsx`; shell [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) ~86 строк. `npm run lint` / `npm run test` зелёные.
- **Area:** [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx), [`useWorkspacePageCore.js`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.js), [`useWorkspacePapersModel.js`](../../ui/src/pages/WorkspacePage/useWorkspacePapersModel.js), [`WorkspaceDialogs.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDialogs.jsx)
- **Raised:** 2026-04-25

### [DONE] Split `ReaderWorkBody.jsx` — chunks list + formatters + claims linking
- **Note (2026-04-26):** Распил: `readerFormatters.js` + тесты, `useReaderWorkData` / `useReaderChunksState` / `useWorkClaims` / `useReaderClaimsFilters`, презентационные `ReaderWorkDetailCard`, `ReaderMarkdownSourcePanel`, `ReaderPdfModeToggle`, `ReaderTraceContextBanner`, `ReaderChunkListPanel`, `ReaderWorkClaimsSection`, `ReaderClaimsListItems`; `ReaderWorkBody.jsx` ~111 строк; `ReaderClaimsPanel` на общем `useWorkClaims`.
- **Area:** [`ReaderWorkBody.jsx`](../../ui/src/components/work/ReaderWorkBody.jsx), [`ReaderClaimsPanel.jsx`](../../ui/src/components/work/ReaderClaimsPanel.jsx), [`PdfViewer.jsx`](../../ui/src/components/work/PdfViewer.jsx)
- **Issue:** Чанки + подсветка + сворачивания + ссылки в graph/ask + слайс `0..4000` в JSX; рост ожидается под Wave O (claims в Reader) и Wave M (страница PDF из цитаты, Wave K2.5).
- **Proposal:** `useReaderChunksState`, `ReaderChunkList`, `readerFormatters.js`; интеграцию с `ReaderClaimsPanel` оставить через композицию.
- **Acceptance:** `ReaderWorkBody.jsx` <= 280 строк; форматтеры покрыты юнитами.
- **Synergy:** **Wave O** (claims production) — UI claims в Reader; **Wave Q/R** (multi-hop, agent answer trace) — кросс-ссылки на работу.
- **Raised:** 2026-04-25

### [DONE] Split `BenchmarkPage/CompareTab.jsx` and `RunTab.jsx` (+ workbench run panel)
- **Note (2026-04-26):** Compare: `benchmarkCompareModel.js` (filter + download), `useCompareTab.js`, `CompareDeltaTable.jsx`, `CompareTabSummarySection.jsx`, `benchmarkCompareModel.test.js`; shell `CompareTab.jsx` ~192 lines. Run: `useRunTab.js` (~288), `RunTabCurrentRunSection.jsx`, `runTabCaseToggle.js`; shell `RunTab.jsx` ~97 lines. Workbench: `workbench/BenchmarkWorkbenchRunPanel.jsx` (`WorkbenchRunScopedPanel` ~318 lines), `BenchmarkWorkbenchTab.jsx` ~157 lines (data fetch only).
- **Area:** [`CompareTab.jsx`](../../ui/src/pages/BenchmarkPage/CompareTab.jsx), [`RunTab.jsx`](../../ui/src/pages/BenchmarkPage/RunTab.jsx), [`BenchmarkWorkbenchTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkWorkbenchTab.jsx), [`workbench/BenchmarkWorkbenchRunPanel.jsx`](../../ui/src/pages/BenchmarkPage/workbench/BenchmarkWorkbenchRunPanel.jsx)
- **Issue:** Сравнение прогонов / запуск конфигурации — крупные tabs, контейнер логики; workbench держал тяжёлую панель в одном файле с shell.
- **Proposal:** Вынести `useCompareDeltas`, `DeltaTable`, `useRunLauncher`, `RunConfigForm`. Хранить metric formatting в общем хелпере.
- **Acceptance:** ни один таб > ≈250 строк.
- **Synergy:** Облегчит добавление UI для **Wave Q/R/P** ablation и judge-метрик.
- **Raised:** 2026-04-25

### [DONE] Условный split `services/researchApi.js` by domain modules
- **Note (2026-04-26):** Barrel [`researchApi.js`](../../ui/src/services/researchApi.js) реэкспортирует `research/{errors,meta,queryModel,queryHttp,askSessions,agent,ideaAssist,works,graph}.js`; `formatResearchApiError` в `errors.js`; крупнейший модуль `queryModel.js` ~137 строк. Отдельные `dedup.js` / `settings.js` / `benchmarks.js` — вынести при росте клиентских вызовов (см. прежний Proposal).
- **Area:** [`services/researchApi.js`](../../ui/src/services/researchApi.js), [`ui/src/services/research/`](../../ui/src/services/research/)
- **Raised:** 2026-04-25 (закрыто 2026-04-26)

### [OPEN] i18n hardcoded copy: HypothesisPanel, IngestionSettings, Workspace dialogs
- **Area:** [`HypothesisPanel.jsx`](../../ui/src/components/work/HypothesisPanel.jsx), [`pages/SettingsPage/IngestionSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx), [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** В этих модулях встречаются хардкод-строки (`Generating...`, `No candidates`, `Workspace summary`, `Hypothesis / contradiction assist`, `Saving…`, `Save ingestion settings`) — расходится с [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md).
- **Proposal:** Вынести в i18n словари, добавить EN+RU ключи, заменить литералы на `t(...)`.
- **Acceptance:** ESLint i18n-проверка зелёная (если включена); ручной аудит не находит литералов в этих компонентах; `npm run lint` зелёный.
- **Raised:** 2026-04-25

### [DONE] Switch dedup dialogs to `Cursor*` button family
- **Note (2026-04-26):** `WorkspaceDedupSection` / `WorkDedupReviewDialog` уже на `Cursor*`; строка Review → `CursorSmallButton` для паритета с `DeduplicationPanel`; прямых `@mui/material/Button` в этих модулях нет.
- **Area:** [`WorkspacePage/WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx), [`graph/dedup/WorkDedupReviewDialog.jsx`](../../ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx)
- **Issue:** Прямое использование MUI `Button` вместо `CursorButton` / `CursorPrimaryButton` / `CursorDangerButton` — расходится с дизайн-каноном (см. `.cursorrules` в osint-gr и общая дисциплина проекта).
- **Proposal:** Заменить импорты на `Cursor*` варианты из `components/common`; учесть варианты `contained/outlined/text`.
- **Acceptance:** ни один прямой импорт `@mui/material/Button` в `WorkspaceDedupSection`/`WorkDedupReviewDialog`; визуальный паритет с остальными dedup-кнопками; `npm run lint` зелёный.
- **Raised:** 2026-04-25

### [DONE] Move `useScienceGraphForceSimulation.js` to `hooks/graph/`
- **Area:** [`hooks/graph/useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js), [`hooks/`](../../ui/src/hooks/)
- **Issue:** ≈425 строк хука лежит в `components/graph/physics/`, рядом со «не-React» утилитами (quadTree, structuralCommunities). В `hooks/` сейчас только `useJobStream`/`usePollJob` — два «места» для сложной async-логики.
- **Proposal:** Перенести хук в `ui/src/hooks/graph/useScienceGraphForceSimulation.js` (или `hooks/useGraphSimulation.js`); оставить чистые модули physics в `components/graph/physics/`.
- **Acceptance:** импорт обновлён в `GraphCanvasMvp`; тесты симуляции зелёные.
- **Raised:** 2026-04-25
- **Done:** 2026-04-26 — хук в `hooks/graph/`; `physics/` только не-React; прямой импорт из `GraphCanvasMvp`.

### [DONE] Workspace UX — Wave WX1 layout & hero (закрывает H-WorkspacePageSlim)
- **Note (2026-04-26):** [`WorkspaceLayout.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceLayout.jsx), [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx), [`WorkspaceSidePanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceSidePanel.jsx) (ingest + graph snapshot + smart-dedup summary + ссылка `#workspace-dedup-section`); убран `maxWidth` у [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx) / [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx); [`WorkspacePaperList.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperList.jsx) — CSS grid 1/2/3 колонки; i18n `workspace.side.*`; [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) ~86 строк; [`WorkspaceLayout.test.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceLayout.test.jsx). Опциональные follow-up из первоначального proposal: `FolderOpenOutlinedIcon` в hero, `WorkspaceSwitcher` inline — остаются на **WX4/WX5**.
- **Area:** см. note
- **Raised:** 2026-04-25

### [DONE] Wave EF-Cards — workspace vs per-paper actions
- **Note (2026-04-26):** На [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx) остались «Чтение» + «Граф статьи»; «Вопросы по области» вынесены в [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx) (`workAskUrl("", workspace_id)`); i18n `workspace.paper.workGraph`, `workspace.actions.askWorkspace`; подсказка на карточке обновлена.
- **Area:** `WorkPaperCard.jsx`, `WorkspaceHero.jsx`, [`workspacePageUrls.js`](../../ui/src/pages/WorkspacePage/workspacePageUrls.js), `partWorkspacePage.js` (EN+RU)
- **Raised:** 2026-04-26

### [DONE] Wave EF-Evidence — `/evidence` без обязательного work_id form
- **Note (2026-04-26):** [`EvidencePage.jsx`](../../ui/src/pages/EvidencePage.jsx): единый `evidence.header.description`; пустое состояние + CTA Workspaces / last workspace; форма `work_id` только при `?dev=1` или admin mode (accordion); `partPagesCore.js` EN+RU.
- **Area:** `EvidencePage.jsx`, `partPagesCore.js` (EN+RU)
- **Raised:** 2026-04-26

### [DONE] Wave EF-Reader — RX1 slice (empty main column, PDF, rail)
- **Note (2026-04-26):** [`useReaderWorkData.js`](../../ui/src/components/work/useReaderWorkData.js) — авто `viewMode=pdf` при `chunks` пустых и PDF доступен; [`ReaderWorkBody.jsx`](../../ui/src/components/work/ReaderWorkBody.jsx) — Alert + «Открыть PDF», предупреждение без PDF/markdown; [`ReaderShell.jsx`](../../ui/src/components/work/ReaderShell.jsx) — колонки 1fr / 240–280, gap 3; [`ReaderWorkDetailCard.jsx`](../../ui/src/components/work/ReaderWorkDetailCard.jsx) — `variant=rail` без дубля title, abstract в Collapse; [`ReaderPage.jsx`](../../ui/src/pages/ReaderPage.jsx) — Advanced только dev/admin; [`ReaderChunkListPanel.jsx`](../../ui/src/components/work/ReaderChunkListPanel.jsx) — hint трассировки; [`PdfViewer.jsx`](../../ui/src/components/work/PdfViewer.jsx) — `console.error` в DEV; [`PdfViewer.test.jsx`](../../ui/src/components/work/PdfViewer.test.jsx); `partReaderBody.js` / `partReaderShell.js` EN+RU. Полный **RX1** (TOC, unify tabs) — открыто в roadmap.
- **Area:** см. note
- **Raised:** 2026-04-26

### [OPEN] Workspace UX — Wave WX2-FE ingest progress card (shimmer + ETA + i18n stages)
- **Area:** новые [`ui/src/components/ingestion/IngestProgressCard.jsx`](../../ui/src/components/ingestion/IngestProgressCard.jsx),
  [`IngestStageRow.jsx`](../../ui/src/components/ingestion/IngestStageRow.jsx);
  [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx);
  [`partWorkspacePage.js`](../../ui/src/i18n/messages/ru/partWorkspacePage.js) (+ EN)
- **Issue:** При активном ingest job UI показывает `<pre>`-блок «Logs» (`Details / Logs` accordion) рядом с
  `IngestStageStepper`. Stepper использует ASCII-символы (`✓ ● ○ ×`), нет общего progress-бара/процента, нет
  shimmer на активной стадии, нет ETA, имена стадий приходят с бэкенда EN-only (`vl_extract`, `embed_chunks`).
  Пользователь не видит «сколько ещё ждать» и не понимает, в какой workspace грузится файл.
- **Proposal:** Новый `IngestProgressCard.jsx`:
  header (filename + size + target workspace name);
  общий `LinearProgress determinate` (значение из `IngestJobView.progress_pct`, fallback — равномерный по `stages.length`);
  список стадий через `IngestStageRow.jsx` (MUI-иконка по статусу: `CheckCircleOutlineOutlinedIcon`/
  `ErrorOutlineOutlinedIcon`/`RotateRightIcon` с `keyframes spin`/`RadioButtonUncheckedOutlinedIcon`;
  локализованное имя через `t("ingest.stage.{name}")`; длительность для завершённых; shimmer-полоса для running);
  ETA-строка из `sum(remaining expected_duration_ms)`;
  «Подробности» accordion свёрнут (внутри — старый `<pre>` с `ingestJob.logs`).
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.2.
- **Acceptance:** При активном job в UI виден только `IngestProgressCard`; «Logs» свёрнут под «Подробности»;
  активная стадия со shimmer, ETA-строка появляется при ≥ 1 завершённой стадии; на ru-локали имена стадий —
  на русском (`Извлечение текста`, `Чанки и эмбеддинги`); `npm run lint` / `npm run test` / новый
  `IngestProgressCard.test.jsx` зелёные.
- **Synergy:** Backend-сторона `IngestJobView.progress_pct` + `expected_duration_ms` —
  отдельный backend-PR (Wave WX2-BE); UI-сторона работает с fallback при отсутствии полей.
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX3-FE ingest-time duplicate card
- **Area:** новые [`ui/src/components/ingestion/IngestDedupCard.jsx`](../../ui/src/components/ingestion/IngestDedupCard.jsx),
  [`services/research/ingest.js`](../../ui/src/services/research/ingest.js);
  [`hooks/useJobStream.js`](../../ui/src/hooks/useJobStream.js);
  [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx)
- **Issue:** При загрузке статьи-дубликата (DOI/arXiv hit или vector ≥ 0.88) backend Wave L1/L2 уже умеет
  обнаружить совпадение, но текущий UI **не показывает confirmation card** прямо в момент ingest.
  Пользователь должен ждать конца pipeline, потом руками открыть `WorkspaceDedupSection` →
  `Scan for near-duplicates` → ручной merge. Принцип «detect → score → user-gated merge»
  ([`_archive/workspace-experience-gap-2026-04-24.md`](../analysis/_archive/workspace-experience-gap-2026-04-24.md) §1.3 — [HISTORICAL]) нарушен.
- **Proposal:** Backend (Wave WX3-BE, отдельный PR) переводит pipeline в стейт `awaiting_user_decision` при hit'е
  и расширяет `IngestJobView.dedup_decision_required: { candidate_work_id, score, match_keys, reason }`.
  Frontend: `useJobStream` реагирует на это поле, показывает `IngestDedupCard` поверх `IngestProgressCard`.
  Карта: 2 колонки (новый work / existing), score, кнопки `Объединить (рекомендуется)` / `Загрузить как отдельную` / `Отмена`.
  Сервис `postIngestDedupDecision(jobId, action)` через `POST /v1/ingest/jobs/{id}/dedup-decision`.
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.3.
- **Acceptance:** При загрузке файла-дубля видна `IngestDedupCard` с правильным score/reason; клик `Объединить`
  возобновляет job в `running`; клик `Отмена` завершает job со статусом `cancelled`; e2e-тест
  `IngestDedupCard.test.jsx` (mock job stream + action click) зелёный; `npm run lint` зелёный.
- **Synergy:** **Зависит от Wave WX3-BE** (новый payload field). Делать после backend-PR merge.
  Соприкасается с Track D Wave T (общий `vector_dedup_check` helper).
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX4 icons & visual hierarchy sweep
- **Area:** [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx),
  [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx) (из WX1),
  [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx),
  [`IngestStageRow.jsx`](../../ui/src/components/ingestion/IngestStageRow.jsx) (из WX2),
  [`WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx),
  [`Cursor*` кнопки](../../ui/src/components/common/) (опционально — поддержка `startIcon`)
- **Issue:** Action-кнопки `Чтение / Граф / Вопросы / Доказательства` на `WorkPaperCard` — голый текст
  (хотя в Drawer те же иконки уже импортированы). В `PageHeader` действия `Граф области` / `Суммировать` /
  `Сгенерировать гипотезы` тоже без иконок. Stage stepper использует ASCII-символы.
- **Proposal:** Добавить MUI-иконки слева у всех action-кнопок: `MenuBookOutlinedIcon` (Чтение),
  `AccountTreeOutlinedIcon` (Граф), `QuestionAnswerOutlinedIcon` (Вопросы), `FactCheckOutlinedIcon` (Доказательства),
  `AutoStoriesOutlinedIcon` (Сводка), `LightbulbOutlinedIcon` (Гипотезы), `UploadFileOutlinedIcon` (Загрузка),
  `CloudUploadOutlinedIcon` (drop-zone), `MergeTypeIcon` (Smart dedup), `BoltOutlinedIcon` (Scan).
  Stage stepper иконки: `CheckCircleOutlineOutlinedIcon` / `RadioButtonUncheckedOutlinedIcon` /
  `ErrorOutlineOutlinedIcon` / `RotateRightIcon` (+ `keyframes spin` для running).
  Если `Cursor*` кнопки не поддерживают `startIcon` — добавить prop через MUI Button base.
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.4.
- **Acceptance:** Все action-кнопки на `WorkspacePage` имеют осмысленную иконку слева; stage stepper использует
  MUI-иконки; running-стадия вращается через `keyframes spin`; `npm run lint` зелёный.
- **Synergy:** Зависит от WX1 (нужен `WorkspaceHero`) и WX2 (нужен `IngestStageRow`).
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX5 workspace switcher + create CTA
- **Area:** новый [`ui/src/components/layout/WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx);
  [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx);
  [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (deprecate/remove);
  [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx) (из WX1);
  [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) (новый empty state)
- **Issue:** «Создать новую workspace» доступно только внутри `WorkspaceContextChip` `Popover` (28×220px chip
  в правом верхнем углу shell-хедера, малозаметен) или на отдельной странице `/workspaces`. На самой `/workspace`
  без активной области показывается info-`Alert` с ссылкой `/workspaces` — пользователь должен покинуть страницу.
- **Proposal:** Расширить `WorkspaceContextChip` в полноценный `WorkspaceSwitcher.jsx`:
  триггер — `Button` h36 с `FolderOpenOutlinedIcon` слева и `ExpandMoreOutlinedIcon` справа;
  popover с searchable списком (search-поле сверху, цветной «аватар» от id, badge `{count}`);
  footer-пиктограммы: `+ Новая` / `⚙ Управлять` / `↗ Открыть текущую`;
  empty state триггера — `Выбрать область` с пунктирной обводкой и subtle pulse animation.
  Использовать switcher и в shell-хедере, и inline в `WorkspaceHero`.
  Empty state в `WorkspacePage.jsx`: большой блок с CTA `+ Новая рабочая область` (создаёт `Workspace N` через
  `createWorkspace` и редиректит) + secondary `Открыть существующую` (открывает switcher popover).
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.4 + §3.5.
- **Acceptance:** На `/workspace` без активной области виден большой CTA «+ Новая»; клик создаёт workspace и
  редиректит на её URL; имя workspace в `WorkspaceHero` кликабельно, открывает switcher; switcher доступен
  в shell-хедере на любой странице; `npm run lint` / `npm run test` зелёные.
- **Synergy:** Зависит от WX1 (нужен `WorkspaceHero`).
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX6 i18n smart-dedup + compact side panel
- **Area:** [`WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx),
  [`WorkDedupReviewDialog.jsx`](../../ui/src/components/graph/dedup/WorkDedupReviewDialog.jsx);
  новый [`ui/src/components/dedup/DedupQueueDialog.jsx`](../../ui/src/components/dedup/DedupQueueDialog.jsx);
  [`partWorkspacePage.js`](../../ui/src/i18n/messages/ru/partWorkspacePage.js) (+ EN)
- **Issue:** EN-хардкод в `WorkspaceDedupSection.jsx`: «Smart dedup (embeddings + LLM)»,
  «Scan for near-duplicates», «Pending», «Review», «No pending smart-dedup conflicts». Кнопка `CursorButton`
  без `Cursor*Primary/Danger` варианта (диссонанс с дизайн-каноном). На основной surface страницы секция
  занимает много места при пустом состоянии.
- **Proposal:** Локализация через `t(...)` (ключи `dedup.smart.title`, `dedup.smart.desc`, `dedup.smart.scan`,
  `dedup.smart.scanning`, `dedup.smart.empty`, `dedup.smart.pending`, `dedup.smart.review`).
  В `WorkspaceSidePanel` (из WX1) — compact-карточка `Smart dedup ▸ {N} конфликтов`, full-list через
  `<DedupQueueDialog>` (новый). На основной surface — оставить `WorkspaceDedupSection` для backward-compat.
  Заменить прямые MUI-`Button` в `WorkDedupReviewDialog` на `Cursor*` family (закрывает существующий пункт
  `H-Cursor*-buttons in dedup` выше). Цвета score: high=`rgba(99,102,241,…)`,
  medium=`rgba(255,193,7,…)`, low=`rgba(239,68,68,…)`.
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.6.
- **Acceptance:** Ни одного EN-литерала в `WorkspaceDedupSection.jsx` / `WorkDedupReviewDialog.jsx`;
  smart dedup section согласован с дизайн-каноном (`Cursor*`, иконки, цвета score);
  в side panel виден compact-card; `npm run lint` / `npm run test` зелёные.
- **Synergy:** Закрывает существующий пункт `H-Cursor*-buttons in dedup` выше; частично закрывает
  `H-i18n-fixes` (часть про Workspace dialogs).
- **Raised:** 2026-04-25

### [OPEN] Batch child jobs: use progress_pct instead of progress_current/total
- **Area:** [`ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx) (строки 159-165)
- **Issue:** Дочерние batch-задания рендерят прогресс через `progress_current / progress_total`. После WX2-BE у child-jobs появился `progress_pct` (float 0..1), но он не используется.
- **Proposal:** В блоке `childJobs.map(...)` добавить fallback: `const pct = typeof cj.progress_pct === "number" && Number.isFinite(cj.progress_pct) ? cj.progress_pct * 100 : ...;` (остальная логика без изменений).
- **Acceptance:** Child-job progress bar отражает взвешенный прогресс стейджей, если backend его возвращает; lint зелёный.
- **Raised:** 2026-04-26

### [OPEN] graph_display: EDGE_DISPLAY_TYPE_READER — reader-specific edge labels
- **Area:** [`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py), [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py)
- **Issue:** `edge_display_type(rel_type, view="reader")` — мёртвая ветка: читает тот же `EDGE_DISPLAY_TYPE_RAW`, что и raw-view. Когда появятся reader-специфичные метки рёбер (например, "AUTHORED" → "authored by" vs "написал"), ветка заглушки не сработает.
- **Proposal:** Создать `EDGE_DISPLAY_TYPE_READER: dict[str, str]` с переопределёнными или добавленными метками; в `edge_display_type` подставить `mapping = EDGE_DISPLAY_TYPE_READER` для reader-view.
- **Acceptance:** `edge_display_type("AUTHORED", view="reader")` возвращает значение из reader-словаря; unit-тест.
- **Raised:** 2026-04-26

### [OPEN] Frontend wiring for `/v2/agent/query` SSE (Wave Y3 follow-up)
- **Area:** [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx), [`hooks/useJobStream.js`](../../ui/src/hooks/useJobStream.js) (как референс), новый `hooks/useAgentStream.js`, `services/research/agent.js`
- **Issue:** Когда backend выкатит `/v2/agent/query` (SSE: `tool_call` / `tool_result` / `token` / `final_answer` / `error`), UI ещё на REST `/v1/agent/query`. Без отдельного refactor-пункта Wave Y6 не сможет удалить v1.
- **Proposal:** Хук `useAgentStream(query, ctx, { onEvent, onTerminal, fallbackPostMs })` поверх `EventSource`; интеграция в `useAskSubmit` (см. AskPanel decomposition); graceful fallback на v1.
- **Acceptance:** при `agent_runtime != "retrieval_v1"` UI открывает один SSE-стрим, рендерит инкрементальный tool trace и финальный ответ; lint/test зелёные.
- **Synergy:** **Wave Y3 → Y6** — необходимое условие удаления `POST /v1/agent/query`.
- **Raised:** 2026-04-25
