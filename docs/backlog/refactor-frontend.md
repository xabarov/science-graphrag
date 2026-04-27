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
| 2026-04-26 | **Workspace UX + ingest dedup (full-stack slice):** full-width `WorkspacePage`; `PageActionToolbar` / `CursorIconAction` / `CopyIdButton` in hero and cards; side panel без smart-dedup poll; удалены `WorkspaceDedupSection`, `DeduplicationPanel`, `WorkDedupReviewDialog`; `IngestConflictReviewCard` + `pending_conflicts_count` на ingest job; икон-действия на Home / Workspaces / Graph / Benchmark / Settings / Diagnostics / Evidence / Admin entry / NotFound / workspace tabs. |
| 2026-04-26 | **Big plan slice (master roadmap phases 0/2/4/5/8 partial):** `scripts/benchmark_aggregator/paths.py` + import из `aggregate_benchmark_metrics.py`; child batch `progress_pct` в `WorkspaceIngestPanel.jsx`; `WorkspaceLayout` stretch + minHeight; `WorkspaceContextChip` (иконка папки, короткий id в списке, title на строке); `EDGE_DISPLAY_TYPE_READER` + тест; `ExtractorBase._safe_parse_json` + `claims_v2`; i18n `settings.ingestion.saveError`; `.env.example` ссылка на ADR-021; `/v2/agent/query` SSE — закрыт пунктом ниже. |
| 2026-04-27 | **WX5 minimal + shell polish:** [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) (re-export chip) в [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx) и [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx); i18n `workspace.hero.switchWorkspaceHint` (EN/RU); chip label без UUID — `shell.workspaceChip.unnamed` когда нет имени ([`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx)); `WorkspaceLayout` — больший `minHeight` grid + flex main. |
| 2026-04-27 | **WX5 empty-state CTA:** кнопка «Новая область» / `workspace.empty.createWorkspace` + `createWorkspace()` и синхрон URL `workspace_id` в [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) empty-state; i18n EN/RU в `partWorkspacePage.js`. |
| 2026-04-27 | **Graph GR-UX1 — command bar:** единая панель [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/WorkspaceGraphToolbar.jsx) — `GraphScopeMenu` / `GraphNodeTypesMenu` / `GraphViewChips` в `toolbar/`, глубина `1°/2°`, тултипы stats, локальный поиск + чипы «Детали / Легенда / Диагностика» в одной строке; [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx) — `Collapse` легенды + `graphEmbeddedLegendOpen`; [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx) — компактный header (overview + sort); [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) — standalone depth как `1°/2°`; i18n `partGraphUi` EN+RU; vitest [`WorkspaceGraphToolbar.test.jsx`](../../ui/src/components/graph/WorkspaceGraphToolbar.test.jsx). |
| 2026-04-27 | **LT1 appearance foundation:** `ui/src/theme/` — `appearanceMode.js`, `buildAppTheme.js` (`appTokens`), `AppearanceProvider.jsx`, inline first-paint в [`ui/index.html`](../../ui/index.html), [`main.jsx`](../../ui/src/main.jsx) без inline `createTheme`; [`styles.css`](../../ui/src/styles.css) по `html[data-color-scheme]`; [`GeneralSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/GeneralSettingsPanel.jsx) + i18n `partSettings` EN/RU; vitest [`appearanceMode.test.js`](../../ui/src/theme/appearanceMode.test.js). Контракт: [`light-theme-roadmap-2026-04-27.md`](../../docs/analysis/light-theme-roadmap-2026-04-27.md) §10. |
| 2026-04-27 | **Ask:** `AskPanel` → [`useAskPanelOrchestration.js`](../../ui/src/components/work/useAskPanelOrchestration.js) + [`AskPanelChrome.jsx`](../../ui/src/components/work/AskPanelChrome.jsx); shell-only [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx). |
| 2026-04-26 | **Graph standalone — scope bugfix:** кнопка «Граф» на [`WorkPaperCard`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx) ведёт на `/graph?work_id=…` без `workspace_id`; [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) больше не подставляет `activeWorkspaceId` в этом случае — иначе [`useGraphWorkspaceData`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) грузил полный workspace graph и игнорировал работу. |

## Queue

### [OPEN] useAgentStream — stable callbacks + abort reason
- **Progress (2026-04-27):** колбэки вынесены в `useRef` + `useEffect`; `stream` стабилен при смене identity колбэков (зависит только от `workspace_id`). Тесты: `useAgentStream.test.js` (rerender + latest `onError`). **Остаётся:** различать причины `AbortError` (навигация / новый submit) для `onError` и «stream ended without final answer».
- **Area:** [`ui/src/hooks/useAgentStream.js`](../../ui/src/hooks/useAgentStream.js)
- **Issue:** `stream` в `useCallback` зависит от нескольких колбэков-ссылок; при `AbortController.abort` нет явного различия между навигацией, HMR reload и новым submit для потребителей `onError`.
- **Proposal:** Паттерн stable callbacks (`useRef` + thin wrapper / `useEvent`), опционально не вызывать `onError` при ожидаемом abort; тест: abort не приводит к ложному «stream ended without final answer» где это нежелательно.
- **Acceptance:** unit-тест на сценарий abort; контракт документирован в комментарии к хуку.
- **Raised:** 2026-04-27

### [OPEN] Agent V2 — EN apology fallback on RU workspace inventory query
- **Progress (2026-04-27):** в user message всегда подмешивается `<active_workspace_id>` из API; `extract_langgraph_answer` берёт текст из tool `final_answer`; усилены промпты retrieval/writer; RU-хинты в `tool_search` / `heuristic_answer_class`. **Остаётся:** прогон `curl`/e2e на реальном workspace и при необходимости принудительный первый tool-call.
- **Area:** [`science_graphrag/api/agent_v2.py`](../../science_graphrag/api/agent_v2.py), цепочка tool selection / system prompt locale
- **Issue:** Запрос вроде «сколько статей в рабочей области?» с валидным `workspace_id` может вернуть `final_answer` на английском с отказом «no necessary tools» вместо осмысленного ответа по данным области.
- **Proposal:** Воспроизвести через `curl` SSE; проверить определение языка ответа, intent/inventory path и доступность тулов для подсчёта работ в workspace.
- **Acceptance:** RU-запрос про объём корпуса области даёт RU-ответ с числом или явным «в области нет работ»; регрессионный тест или зафиксированный benchmark-case по желанию.
- **Raised:** 2026-04-27

### [OPEN] Workspace shell — «Research» chip, dropdown noise, пустая зона под карточками
- **Progress (2026-04-27):** см. Completed (WX5 minimal, empty-state **create workspace** CTA, chip `unnamed`, layout `minHeight`). **2026-04-26:** searchable switcher в popover (фильтр по имени/id), счётчик работ, сортировка, тонкий скролл, компактный футер с иконками — см. [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (~356 LOC; при refactor-pass вынести строку/панель). **Остаётся:** второй ряд контента под карточками (ingest/dedup/illustration), улучшение копирования id из строки списка.
- **Area:** [`DashboardLayout`](../../ui/src/components/layout/DashboardLayout/), [`WorkspaceContextChip`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (или аналог триггера «Research»), [`WorkspaceLayout.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceLayout.jsx) / [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** Чип в углу слабо аффордирует «смена области»; в списке под именем длинный UUID — визуальный шум (мы уже убрали id с hero, но chip всё ещё дублирует низкоуровневый id). Под сеткой карточек остаётся большая пустая область — layout не тянет main на высоту viewport / нет явного второго ряда контента (ingest progress, dedup, пустой state illustration).
- **Proposal:** (1) Заменить или дополнить чип: иконка области + короткое имя без UUID в основной строке (id в tooltip / «Копировать id»). (2) Рассмотреть `WorkspaceSwitcher` из backlog WX5 как primary entry. (3) Main column: `flex: 1` + `minHeight` / placeholder или закрепить `IngestConflictReviewCard` / ingest stepper внизу колонки при наличии событий.
- **Acceptance:** скринлист до/после; нет горизонтального «дырявого» ощущения на 1440×900; `npm run lint` зелёный.
- **Raised:** 2026-04-26

### [OPEN] Ingest conflict UI — osint-grade `ConflictResolver` (типы сущностей + inline к job)
- **Area:** [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx), [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx), `useJobStream` / ingest job types
- **Issue:** Текущая карточка — упрощённый мастер по **work** парам после завершения job (или при открытой панели). Нет разветвления по author/entity, нет side-by-side «карточек сущности» как в osint `ConflictResolver.jsx`, нет привязки к **активному** стриму ingest (пользователь не видит «решить сейчас», пока job не завершён — если нет pending в очереди).
- **Proposal:** После backend-расширения (см. `refactor-backend.md` — ingest dedup parity): унифицировать модель «конфликт» для UI; для works — расширить карточку (метаданные, score, match keys); при появлении API mid-job — блок поверх `IngestProgressCard` или drawer. Референс UX: `osint-gr/frontend/src/pages/KnowledgeGraphPage/components/ConflictResolver.jsx` + `RightPanel.jsx`.
- **Acceptance:** e2e или component-тест на смену состояний; i18n для новых полей; не деградирует текущий happy path без конфликтов.
- **Raised:** 2026-04-26

### [OPEN] Remove deprecated workspace dedup HTTP surface (after soak)
- **Area:** `science_graphrag/api/workspace_dedup.py` (или аналог), фронт уже не вызывает scan/merge/candidates из `GraphPage` / side panel.
- **Issue:** Backend endpoints `/v1/workspaces/.../dedup/*` остаются для обратной совместимости; мёртвый API усложняет security review.
- **Proposal:** После 1–2 релизов без внешних клиентов — удалить неиспользуемые маршруты или спрятать за feature flag; оставить только то, что использует `IngestConflictReviewCard` (`getWorkspaceSmartDedupConflicts`, `decideWorkspaceSmartDedupConflict`).
- **Acceptance:** grep по `ui/` не находит удалённых путей; OpenAPI / тесты обновлены; CHANGELOG note.
- **Raised:** 2026-04-26

### [DONE] Graph canvas — Neo4j Browser–grade UX (slice: double-click fit selection)
- **Note (2026-04-26):** `graphCanvasCamera.js` (`buildPositionSubset`, `computeFitTransformForNodeSubset`) + `graphCanvasCamera.test.js`; `GraphCanvasMvp.jsx` — `onDoubleClick` на canvas вписывает вид в bbox текущего `selectedNodeId` (как full fit, с тем же `NODE_RADIUS` / padding / `MIN_FIT_SCALE`). i18n: `graph.canvas.helpTooltip`, `helpAria`, `regionAria` (EN+RU). Мультивыделение — когда появится на уровне workspace, прокинуть iterable id в тот же helper.
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`graphCanvasCamera.js`](../../ui/src/components/graph/graphCanvasCamera.js), [`partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js) (EN+RU)
- **Raised:** 2026-04-08; closed slice 2026-04-26

### [DONE] Graph standalone — paper card link must not inherit active workspace
- **Note (2026-04-26):** В `GraphPage.jsx` для `effectiveWorkspaceId`: если в URL есть `work_id`, fallback на `activeWorkspaceId` из shell отключён — используется только `workspace_id` из query (если есть). Без этого ссылка с карточки статьи открывала граф всей рабочей области. Опциональный follow-up: URL с обоими `work_id` + `workspace_id` и доработка `useGraphWorkspaceData` для «работа в контексте области» без замены на полный `getWorkspaceGraph`.
- **Area:** [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx), [`useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js), [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx)
- **Raised:** 2026-04-26; **Done:** 2026-04-26

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
- **Note (2026-04-26):** Исторически `WorkspaceDedupSection` / `WorkDedupReviewDialog` переведены на `Cursor*`. **2026-04-26:** эти компоненты и graph `DeduplicationPanel` удалены; review — в [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx) (`CursorSmallButton` / actions).
- **Area:** (архив) удалённые `WorkspaceDedupSection.jsx`, `WorkDedupReviewDialog.jsx`; актуально — [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx)
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

### [DONE] Wave EF-Reader — RX1 cleanup (single-column reader, PDF responsive width)
- **Note (2026-04-26):** Пользовательское ревью UX страницы `/reader` показало регрессию исходного RX1 slice: правый rail (`ReaderShell` + `ReaderSideRail` + `ReaderWorkDetailCard variant="rail"`) дублировал аннотацию, которую в основной колонке заодно показывал `ReaderMarkdownSourcePanel sourceVariant="abstract"` (fallback, когда `chunks.total === 0`). PDF в этом layout сжимался до ~50–60 % колонки из-за `Page scale={1.1}` без width-fitting; пустой блок `Чанки (дополнительно) — 0` оставлял большое пустое поле под viewer'ом. Решение: одноколоночный layout. [`ReaderWorkBody.jsx`](../../ui/src/components/work/ReaderWorkBody.jsx) — убран `layoutVariant`, всегда single column, fallback abstract panel удалён, `ReaderChunkListPanel` и chunks hint скрыты при `!hasEffectiveChunks`. [`ReaderWorkDetailCard.jsx`](../../ui/src/components/work/ReaderWorkDetailCard.jsx) — единый компактный card: метастрока (year · DOI · arXiv) + collapsible-кнопка `Аннотация` (collapsed по умолчанию, аннотация ограничена `maxWidth: 78ch`). [`ReaderMarkdownSourcePanel.jsx`](../../ui/src/components/work/ReaderMarkdownSourcePanel.jsx) — единственный вариант («extracted»), измеренный читательский measure 78ch, увеличенный viewport (`maxHeight: calc(100vh - 280px)`). [`PdfViewer.jsx`](../../ui/src/components/work/PdfViewer.jsx) — `ResizeObserver` + `Page width={…}` (responsive ширина по контейнеру с capов 280–1280 px), zoom-controls со счётчиком процентов, single-source-of-truth сброс zoom/page при смене `fileUrl` через render-time state-reset; viewer фиксируется в центре, `maxHeight: calc(100vh - 260px)`, `minHeight: 480`. [`ReaderPage.jsx`](../../ui/src/pages/ReaderPage.jsx) — без `flex: 1` на body (контент даёт натуральную высоту, исчезает пустое поле снизу). [`ReaderShell.jsx`](../../ui/src/components/work/ReaderShell.jsx), [`ReaderSideRail.jsx`](../../ui/src/components/work/ReaderSideRail.jsx) удалены; ключи `readerShell.tocSection*`, `readerBody.abstractFallback*` (EN+RU) вычищены. `npm run lint` / `vitest run` (208 тестов) / `npm run build` зелёные.
- **Area:** см. note
- **Raised:** 2026-04-26

### [OPEN] Wave EF-Reader — RX2 reading affordances (TOC, language banner, copy-id)
- **Area:** новые `ReaderToc.jsx` (или встраивание в header), `ReaderLanguageBanner.jsx`, `ReaderCopyWorkIdButton.jsx`;
  [`ReaderWorkDetailCard.jsx`](../../ui/src/components/work/ReaderWorkDetailCard.jsx),
  [`ReaderPage.jsx`](../../ui/src/pages/ReaderPage.jsx),
  [`ReaderTab.jsx`](../../ui/src/pages/WorkspacePage/tabs/ReaderTab.jsx)
- **Issue:** После RX1 cleanup страница «Чтение» одноколоночная, но без навигации по разделам (TOC), без явного индикатора языка статьи (для будущей кнопки перевода) и без ergonomic copy-кнопки `work_id`. Длинные статьи (`Page width = container width`, ~1000 px) дают comfortable measure только при принудительной 78ch — но без TOC прыгать по секциям трудно. Roadmap RX1 (`docs/analysis/reader-ux-and-translation-roadmap-2026-04-25.md` §1.4–§1.6) предполагает левую/правую полоску либо overlay TOC.
- **Proposal:**
  1. `ReaderToc.jsx` строит дерево из `chunks[].section_path`, рендерит как right-side `position: sticky` panel при `lg+` (collapsible button под header при `<lg`); клик по узлу делает `scrollIntoView` соответствующего markdown-блока (нужно расставить anchor-id из `section_path` в `MarkdownView` / `ReaderMarkdownSourcePanel`).
  2. `ReaderLanguageBanner.jsx` — компактная плашка под `ReaderWorkDetailCard` с `detail.language` (когда backend начнёт отдавать), placeholder при `auto/unknown`; кнопки `Перевести аннотацию / Перевести статью` (отключены до Wave LX-2 backend).
  3. `ReaderCopyWorkIdButton.jsx` — мелкая `IconButton` (small caps `work_id`) рядом с метастрокой; копирует `workId` в clipboard.
  4. Объединить `ReaderTab` + `ReaderPage` через общий контент-компонент: один и тот же layout, разные обвязки header'ом.
- **Acceptance:** `npm run lint` / `vitest run` (новые тесты на `ReaderToc` парсинг section_path) / `npm run build` зелёные; на ноутбуке (1440×900) видны header + TOC + body без горизонтального скролла; в workspace-табе `Reader` тот же body без дубликации детальной шапки.
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

### [DONE] Workspace UX — Wave WX3-FE ingest conflicts (queue + review card)
- **Note (2026-04-26):** Вместо mid-pipeline `IngestDedupCard` + `awaiting_user_decision` реализован **post-write** поток: `ingest_conflict_check` ставит `WorkDedupConflict` с `origin=ingest`; job DTO — `pending_conflicts_count`; UI — [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx) на [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx). Опциональный follow-up из старого proposal (блокировка job + `dedup_decision_required`) — отдельный пункт если понадобится.
- **Area:** `ui/src/components/dedup/`, `useWorkspacePageCore.jsx`, `workspaceStore.js`, ingest job types
- **Raised:** 2026-04-25; **Done:** 2026-04-26

### [DONE] Workspace UX — Wave WX4 icons & visual hierarchy (toolbar pattern)
- **Note (2026-04-26):** `CursorIconAction`, `PageActionToolbar`, `CopyIdButton`; hero + paper cards + основные страницы (Home, Workspaces, Graph popover, Benchmark bar, Settings, Diagnostics, Evidence, NotFound, Admin entry) и workspace tabs (Overview/Reader/Graph/Evidence) переведены на **icon + tooltip**. `WorkspaceDedupSection` удалён. Остаётся OPEN: ingest stepper ASCII (WX2), `WorkspaceIngestPanel` текстовые primary на загрузке — см. WX2 / ниже follow-up.
- **Area:** `ui/src/components/common/CursorIconAction.jsx`, `ui/src/components/layout/PageActionToolbar.jsx`, перечисленные страницы
- **Raised:** 2026-04-25; **Done:** 2026-04-26 (часть scope перенесена в WX2-FE)

### [OPEN] Workspace UX — Wave WX4 follow-up: ingest panel primary labels + stepper icons
- **Area:** [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx), [`IngestStageStepper`](../../ui/src/components/ingestion/) (или аналог)
- **Issue:** После WX4 основной паттерн навигации — иконки; крупные текстовые «Добавить работу» / drop-zone на ingest остаются намеренно читаемыми; stepper всё ещё может использовать ASCII-маркеры до WX2.
- **Proposal:** По продуктовому решению: либо оставить текст на primary ingest CTA, либо добавить `startIcon` + короткий label; stepper — в WX2-FE.
- **Acceptance:** единый визуальный язык с остальным приложением без потери ясности для upload.
- **Raised:** 2026-04-26

### [DONE] Workspace UX — Wave WX5 workspace switcher (minimal v1)
- **Note (2026-04-27):** Реализован **minimal slice** из roadmap: [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) подключён в [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx) (shell) и в [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx) (toolbar при активной области + строка подсказки при отсутствии области); тот же компонент технически реэкспортирует `WorkspaceContextChip` (Popover с «Создать» / «Управление» сохранён). **Не реализовано** относительно исходного proposal: searchable список, dashed empty-trigger, отдельный megatron empty-state на [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx) — приоритизировать в follow-up если UX-метрики потребуют.
- **Area:** как выше + i18n `workspace.hero.switchWorkspaceHint`, `shell.workspaceChip.unnamed`
- **Acceptance (факт v1):** switcher виден в shell и в hero; без активной области — подсказка + доступ к созданию через существующий popover; `npm run lint` зелёный на затронутых файлах.
- **Synergy:** WX1 ✅
- **Raised:** 2026-04-25; **Done:** 2026-04-27 (minimal)

### [OPEN] Workspace UX — Wave WX5 follow-up (searchable list + richer switcher)
- **Area:** [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) (реальная обёртка вместо re-export), [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx)
- **Progress (2026-04-27):** on-page **«New workspace»** (`workspace.empty.createWorkspace`) в empty-state [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) — создаёт область и обновляет `workspace_id` в URL.
- **Issue:** Список областей в popover по-прежнему не searchable; триггер — старый Chip, не отдельная кнопка h36 из исходного макета.
- **Proposal:** Вынести разметку из `WorkspaceContextChip` в составной `WorkspaceSwitcher` (или расширить chip props); empty state блок на `WorkspacePage` по [`workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.5.
- **Acceptance:** как в старом OPEN WX5 (megatron CTA + search) **или** осознанно сузить продуктовый scope и обновить ADR/workspace doc.
- **Raised:** 2026-04-27

### [DONE] Workspace UX — Wave WX6 superseded (ingest conflict card replaces smart-dedup surface)
- **Note (2026-04-26):** `WorkspaceDedupSection` / `WorkDedupReviewDialog` / graph `DeduplicationPanel` удалены; очередь конфликтов — через smart-dedup API + `IngestConflictReviewCard` (i18n `workspace.ingestDedup.*`). Опциональный отдельный `DedupQueueDialog` не требуется для текущего продукта.
- **Area:** удалённые компоненты; [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx)
- **Raised:** 2026-04-25; **Done:** 2026-04-26

### [DONE] Batch child jobs: use progress_pct instead of progress_current/total
- **Note (2026-04-26):** [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx) — при валидном `cj.progress_pct` (0..1) полоса берёт `*100`, иначе прежний расчёт по `progress_current`/`progress_total`.
- **Area:** см. note
- **Raised:** 2026-04-26

### [DONE] graph_display: EDGE_DISPLAY_TYPE_READER — reader-specific edge labels
- **Note (2026-04-26):** [`graph_display.py`](../../science_graphrag/api/graph_display.py) — `EDGE_DISPLAY_TYPE_READER` с override для `CITES`/`AUTHORED`/`HAS_AUTHORSHIP`; тест в [`tests/storage/test_graph_display.py`](../../tests/storage/test_graph_display.py). Дальнейшие ключи — по продукту (i18n на API-строках остаётся отдельной волной GR7).
- **Area:** см. note
- **Raised:** 2026-04-26

### [DONE] Frontend wiring for `/v2/agent/query` SSE (Wave Y3 follow-up)
- **Note (2026-04-26):** Реализовано: [`useAgentStream.js`](../../ui/src/hooks/useAgentStream.js) (fetch + `text/event-stream` reader + `flushSseBuffer`) и интеграция в [`useAskSubmit.js`](../../ui/src/components/work/useAskSubmit.js) при agent mode + streaming. Fallback на JSON и v1 остаётся в `useAskSubmit`. **Остаётся OPEN на Wave Y6:** удаление/deprecate `POST /v1/agent/query` когда backend зафиксирует v2-only.
- **Area:** см. note
- **Raised:** 2026-04-25; **Done:** 2026-04-26 (инкремент; v1 removal — отдельный пункт при Y6)
