# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Queue

### [DONE] Graph canvas — Wave 4.2 z-order (labels vs nodes)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md)
- **Issue:** Подписи рёбер и узлы пересекались: edge labels рисовались до дисков узлов и прятались под ними; нужен порядок «hovered/selected сверху».
- **Proposal:** Переставить этапы отрисовки; сортировки по rank + стабильный tie-break по `id`.
- **Acceptance:** Спека *Canvas micro-polish (Wave 4.2)*; линт/тесты UI зелёные.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано в `GraphCanvasMvp.jsx`; раздел Wave 4.2 в graph-ui-plan.

### [DONE] Graph standalone page — максимизация рабочей области (Wave 5)
- **Area:** [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx), [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx)
- **Issue:** Канвас графа на `/graph` не заполняет доступную высоту; много вертикального места занимают заголовок, форма `work_id`, алерты, легенда, колонка деталей.
- **Proposal:** Цепочка flex + `minHeight: 0` от `main`; сворачиваемый chrome страницы; компактные/сворачиваемые алерты и легенда; скрытие колонки деталей; опционально `?compact=1`. См. раздел *Standalone Graph page — workspace maximization* в [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md).
- **Acceptance:** В типичном viewport с загруженным `work_id` и режиме Graph канвас занимает большую часть экрана; детали и вторичный UI доступны без потери функций.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано: flex-цепочка в `DashboardLayout`, переработка `GraphPage` (chrome + `compact`), standalone-панель с toggles legend/details/alerts.

### [DONE] Graph standalone — focus URL + detail column width (Wave 6)
- **Area:** [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx), [`graphPageUrl.js`](../../ui/src/pages/graphPageUrl.js), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md), [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md)
- **Issue:** После Wave 5 оставались опциональные URL `focus=1` и настройка ширины колонки деталей; контракт query для `/graph` не был собран в одном месте.
- **Proposal:** `?focus=1` + сохранение флагов при Load; `focusLayout` в панели; слайдер min-width колонки деталей + `localStorage`; тесты `graphPageUrl`; документация Wave 6 и таблица в frontend-ui-api-contracts.
- **Acceptance:** Deep link с `focus=1` даёт максимум места канвасу; ширина деталей настраивается и переживает reload; линт/тесты UI зелёные.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано: `graphPageUrl.js`, `focusLayout`, слайдер `graphStandaloneDetailMinPx`, раздел Wave 6 в graph-ui-plan и таблица `/graph` в frontend-ui-api-contracts.

### [DONE] Graph standalone — drag-resize gutter graph/detail (Wave 7)
- **Area:** [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`graphDetailColumnWidth.js`](../../ui/src/components/graph/graphDetailColumnWidth.js), [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md)
- **Issue:** После Wave 6 оставался опциональный **drag** сплита между графом и колонкой деталей (slider уже был).
- **Proposal:** Третья колонка 6px в grid на `md+`, `pointer` resize, общий clamp и ключ `graphStandaloneDetailMinPx`; утилита + тесты.
- **Acceptance:** На широком layout разделитель тянет ширину деталей в пределах 260–480px, значение синхронно со слайдером и переживает reload.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано: `graphDetailColumnWidth.js`, gutter в `GraphWorkspacePanel`, раздел Wave 7 в graph-ui-plan.

### [DONE] Graph standalone — contract doc + gutter drag polish (Wave 8)
- **Area:** [`frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md)
- **Issue:** После Wave 7 в контракте UI не было явной строки про **client-only** `graphStandaloneDetailMinPx` и gutter; drag без pointer capture мог терять события и выделять текст.
- **Proposal:** Абзац в frontend-ui-api-contracts под `/graph`; `setPointerCapture` + восстановление `cursor`/`user-select` на body при drag; короткий Wave 8 в graph-ui-plan.
- **Acceptance:** Читатель контракта видит, что ширина деталей не в API; перетаскивание разделителя стабильнее на `md+`.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано: параграф в frontend-ui-api-contracts, правка `handleDetailSplitPointerDown`, Wave 8 в graph-ui-plan.

### [DONE] Research API — единый `formatResearchApiError`
- **Area:** [`researchApi.js`](../../ui/src/services/researchApi.js), страницы/панели с catch от `getWorks` / Ask / graph / settings / benchmarks
- **Issue:** Повторялся один и тот же разбор `err?.response?.data?.detail` vs `message`.
- **Proposal:** Экспорт `formatResearchApiError(err)`; вызовы в компонентах и `humanizeLauncherError`; тесты в [`researchApi.test.js`](../../ui/src/services/researchApi.test.js).
- **Acceptance:** Линт/тесты UI зелёные; поведение сообщений об ошибках не регрессирует (string detail, JSON detail, message).
- **Raised:** 2026-04-08
- **Note (done):** Реализовано в `researchApi.js` и заменены дубли в UI.

### [DONE] Graph — Wave 4.3 React Flow POC (library path)
- **Area:** [`GraphFlowView.jsx`](../../ui/src/components/graph/GraphFlowView.jsx), [`graphFlowAdapter.js`](../../ui/src/components/graph/graphFlowAdapter.js), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`package.json`](../../ui/package.json) (`@xyflow/react`)
- **Issue:** Нужна оценка библиотечного рендера графа без смены API-контракта.
- **Proposal:** Режим **Flow** (третья кнопка рядом с Cards / Graph): те же `normalizeGraphPayload` + `capGraphForUi`, круговые стартовые координаты как у Canvas, выбор узла/ребра, `GraphDetailPanel`.
- **Acceptance:** ADR 006 обновлён; *Layout stack* в `graph-ui-plan.md`; линт/тесты UI зелёные.
- **Raised:** 2026-04-08
- **Note (done):** Реализовано 2026-04-08; по умолчанию по-прежнему Canvas.

### [DONE] Graph layout — Canvas force (QuadTree / communities) + follow-ups
- **Area:** `ui/src/components/graph/` (`GraphCanvasMvp.jsx`, `physics/`, `graphSimulationAdapter.js`)
- **Issue:** Нужна была **силовая** раскладка на Canvas по мотивам osint-gr без смены API-контракта.
- **Proposal:** Реализовано: Circle | Force в `GraphWorkspacePanel`, `useScienceGraphForceSimulation`, ADR 007. Опционально позже: **Sigma** spike, force на **Flow**, углублённый паритет с osint controls.
- **Acceptance:** ADR 007 + *Layout stack* в `graph-ui-plan.md`; выбор/URL/`GraphDetailPanel`/лимиты сохранены.
- **Raised:** 2026-04-08
- **Note (done):** 2026-04-08 — см. [`docs/adr/007-canvas-force-layout-port.md`](../adr/007-canvas-force-layout-port.md). Открытым остаётся сравнение с Sigma / force-flow только при продуктовом запросе (новый пункт при необходимости).

### [DONE] Ingest UI — switch from polling to `useJobStream` (Wave U/V)

- **Area:** [`usePollJob.js`](../../ui/src/hooks/usePollJob.js), [`WorkspacePage/WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx) (и любые другие места `setInterval`-поллинга `/v1/ingest/jobs/{id}`)
- **Issue:** UI каждые 2 с дёргает `GET /v1/ingest/jobs/{id}`; пользователь видит фиксированный `message` («Running pipeline (Neo4j / vectors / SQL)…»), стадию пайплайна не понять; access-лог зашумлён.
- **Proposal:** в две стадии по [docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md](../analysis/ingestion-async-pipeline-roadmap-2026-04-25.md):
  - **Wave U (UI):** компонент `IngestStageStepper` рендерит `job.stages[]` (новое поле `IngestJobView.stages` от backend), polling остаётся.
  - **Wave V (UI):** хук `useJobStream(jobId, { onEvent, onTerminal, fallbackPollMs })` поверх `EventSource` к `/v1/ingest/jobs/{id}/events`; graceful fallback на `usePollJob` при reconnect-фейлах. `usePollJob` остаётся как named export.
- **Acceptance:** в WorkspacePage при ingest одного PDF — одно долгое HTTP-соединение `/events` в DevTools вместо периодических `GET /jobs/{id}`; степпер показывает все 10 стадий со статусами и метриками; `npm run lint` / `npm run test` зелёные.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — Wave U + V закрыты: `IngestStageStepper`, `useJobStream`, fallback на polling, и интеграция в `WorkspacePage` доставлены.

### [OPEN] Graph canvas — Neo4j Browser–grade UX (optional)
- **Area:** `GraphCanvasMvp.jsx`, при необходимости отдельный hook
- **Issue:** Сделано: force restart, unpin, +/- / 0 keyboard zoom/fit, tooltips. В Neo4j Browser ещё есть command bar, стили рёбер по типу, инспектор запросов, контекстное меню, экспорт — не требуются для read-only neighborhood v1.
- **Proposal:** По продукту — контекстное меню узла, легенда типов рёбер на canvas, double-click fit selection; не раздувать MVP без запроса.
- **Acceptance:** N/A до приоритизации.
- **Raised:** 2026-04-08

### [DONE] Graph canvas — split `GraphCanvasMvp` (input vs physics vs draw)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx)
- **Issue:** Файл ~1000+ строк: pointer/transform, wiring симуляции и отрисовка canvas в одном модуле; после force/reheat правок рост риска регрессий.
- **Proposal:** Вынести pointer/pan/drag/select в `useGraphCanvasInput` (или модуль рядом), fit/transform в утилиту/hook, оставить в компоненте только glue + `draw` либо `graphCanvasDraw.js`.
- **Acceptance:** оркестратор canvas без «god file» (heuristic: &lt;400 строк или явно разделённые слои); поведение drag/pan/force без регрессий; `npm run lint` / `npm run test` зелёные.
- **Raised:** 2026-04-19
- **Note (done):** 2026-04-25 (Round 5) — разнесено на `GraphCanvasMvp.jsx` (shell),
  `hooks/useGraphCanvasInput.js`, `graphCanvasDraw.js`; добавлен рендер агрегатор badge и smoke-test `graphCanvasDraw.test.js`.

### [DONE] Graph UI — Aggregator rendering + expand-on-click
- **Area:** [`graphCanvasStyle.js`](../../ui/src/components/graph/graphCanvasStyle.js), [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`GraphDetailPanel.jsx`](../../ui/src/components/graph/GraphDetailPanel.jsx), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`hooks/useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js), [`researchApi.js`](../../ui/src/services/researchApi.js)
- **Note (done):** 2026-04-25 — стиль Aggregator (пунктир), expand по клику в canvas/details, merge раскрытых узлов/рёбер в локальный graph state через `expandAggregator`.

### [OPEN] Graph UI — Wave GR6 use displayType on canvas (closes Wave GR2 frontend gap)
- **Area:** [`graphCanvasDraw.js`](../../ui/src/components/graph/graphCanvasDraw.js),
  [`graphCanvasStyle.js`](../../ui/src/components/graph/graphCanvasStyle.js),
  [`graphCanvasDraw.test.js`](../../ui/src/components/graph/graphCanvasDraw.test.js)
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

### [OPEN] Graph UI — Wave GR7 i18n EN/RU for graph edges, node kinds, aggregator labels
- **Area:** [`ui/src/i18n/messages/en/partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js),
  [`ui/src/i18n/messages/ru/partGraphUi.js`](../../ui/src/i18n/messages/ru/partGraphUi.js),
  новый `ui/src/components/graph/graphLocalize.js`,
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

### [DONE] Workspaces page — split shell vs indexed-works browser (Wave I)
- **Area:** [`WorkspacesPage.jsx`](../../ui/src/pages/WorkspacesPage.jsx), [`WorkspacesPage/WorkspaceCollectionPanel.jsx`](../../ui/src/pages/WorkspacesPage/WorkspaceCollectionPanel.jsx), [`WorkspacesPage/WorkspaceRecentPanel.jsx`](../../ui/src/pages/WorkspacesPage/WorkspaceRecentPanel.jsx), [`WorkspacesPage/IndexedWorksBrowser.jsx`](../../ui/src/pages/WorkspacesPage/IndexedWorksBrowser.jsx)
- **Done:** 2026-04-24 — composition shell + extracted panels; `npm run lint` / `npm run test` green.

### [DONE] Workspace page — split upload / dedup / paper list (Wave I)
- **Area:** [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx), [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx), [`WorkspacePaperList.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperList.jsx), [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx), [`WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx)
- **Done:** 2026-04-24 — shell coordinates URL + meta; `npm run lint` / `npm run test` green.

### [DONE] AskPanel decomposition after Wave R agent mode
- **Area:** [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx), [`AgentToolTrace.jsx`](../../ui/src/components/work/AgentToolTrace.jsx)
- **Issue:** После добавления `agent` режима в Wave R `AskPanel` остаётся большим модулем с несколькими ответственностями (session state, submit flows, retrieval/agent trace rendering). Файл — 841 строка.
- **Proposal:** Вынести submit orchestration (`useAskSubmit`), session controls (`AskSessionControls`) и answer sections (`AskAnswerPanel`) в отдельные модули; оставить в `AskPanel` только composition layer.
- **Acceptance:** Ни один модуль в `ui/src/components/work/` по этому флоу не превышает ~400 строк; `npm run lint` / `npm run test` зелёные.
- **Synergy:** **Wave Y3** (`/v2/agent/query` SSE) — `useAskSubmit` будет точкой переключения REST→SSE без правки UI-каркаса; **Wave Y4** (multi-agent supervisor) — `AskAnswerPanel` сразу подцепит `routing_log` без раскопок в god-файле.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `useAskSubmit.js` (submit orchestration),
  `AskSessionControls.jsx` (input + buttons), `AskAnswerPanel.jsx` (answer + citations + trace);
  `AskPanel.jsx` = composition shell ≤280 строк; Wave Y3 SSE переключается только в `useAskSubmit`.

### [DONE] Split `GraphWorkspacePanel.jsx` (1164) — data hook vs view modes vs debug
- **Area:** [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx), [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`GraphFlowView.jsx`](../../ui/src/components/graph/GraphFlowView.jsx), [`graphViewState.js`](../../ui/src/components/graph/graphViewState.js), [`mergeWorkspaceRawGraph.js`](../../ui/src/components/graph/mergeWorkspaceRawGraph.js)
- **Issue:** Файл ≈1164 строки. Совмещает: загрузку/мердж графа, переключение Cards/Canvas/Flow, боковую колонку деталей, drag-resize gutter, легенду, raw JSON inspector, алерты, `formatResearchApiError`.
- **Proposal:** Вынести `useGraphWorkspaceData` (fetch + merge + retry + кеш neighbors), `GraphViewModeSwitch` (Cards/Canvas/Flow), `GraphDebugInspector` (raw JSON + diagnostic), `GraphSidePanel` (колонка деталей + gutter из существующего `graphDetailColumnWidth.js`); оставить в `GraphWorkspacePanel` только composition + URL state.
- **Acceptance:** ни один модуль в `components/graph/` не превышает ~500 строк (кроме `GraphCanvasMvp` — отдельный пункт); `npm run lint` / `npm run test` зелёные.
- **Synergy:** **Wave GR2/GR3/GR4** (агрегаторы + reader view + prioritized LIMIT) — сразу видно, какой компонент трогать; добавление UI для `aggregator_id` expand идёт в `GraphSidePanel` без god-файла; легенда `node_kind` правится отдельно.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — разнесено на `hooks/useGraphWorkspaceData.js`, `GraphViewModeSwitch.jsx`, `GraphSidePanel.jsx`, `GraphDebugInspector.jsx`; `GraphWorkspacePanel.jsx` оставлен как composition-shell с прежним публичным API.

### [OPEN] Benchmark trust drill-in (`TrustSignalPanel` + API slice)
- **Area:** [`TrustSignalPanel.jsx`](../../ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx), [`benchmark_decision_gate.py`](../../science_graphrag/api/benchmark_decision_gate.py) (optional: extend response), i18n `partBenchmarkPage.js`.
- **Issue:** API already returns `trust_signal.consistency_warnings`, `validation_status_aggregate`, and `criteria.advisory_individual_failures`; UI only shows decision chip + `runtime_mode` rows — operators cannot drill into failed case_ids without opening raw JSON.
- **Proposal:** Expandable rows or secondary panel: show `consistency_warnings`, `validation_status_aggregate`, and a compact table for `criteria.advisory_individual_failures` (case_id, family.member); extract presentational helpers to `TrustSignalDrillIn.jsx` when file approaches ~250 lines.
- **Acceptance:** `/benchmark` shows actionable drill-in for judge failures and phantom warnings; `npm run lint` / vitest green.
- **Synergy:** **Round 6 BT2–BT5** — more fields in summary; avoid growing `TrustSignalPanel.jsx` into a god-component.
- **Raised:** 2026-04-26 (post-BT1).

### [OPEN] Split `BenchmarkPage/CaseDetailDialog.jsx` (790)
- **Area:** [`BenchmarkPage/CaseDetailDialog.jsx`](../../ui/src/pages/BenchmarkPage/CaseDetailDialog.jsx), смежные `BenchmarkPage/{CompareTab,RunTab,BenchmarkWorkbenchTab,BenchmarkRunCasesTable}.jsx`
- **Issue:** Один диалог с превью кейса, таблицами gold vs pred, server preview, ошибками; работает в трёх вкладках. С добавлением новых семейств (`workspace_scoped`, `hybrid_ablation`, `multihop`, `agent_tools`, `idea_assist`) растёт линейно.
- **Proposal:** Вынести `CasePreviewTable`, `GoldVsPredSection`, `useCaseDetailDialogData` (fetch + ошибки + кеш). Семейство-специфичные превью — в `pages/BenchmarkPage/families/<family>.jsx`.
- **Acceptance:** ни один файл в `pages/BenchmarkPage/` не превышает ~400 строк; добавление нового семейства бенчмарков требует только нового `families/<name>.jsx` + регистрации.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap` — постоянно добавляются семейства бенчмарков.
- **Raised:** 2026-04-25

### [OPEN] Slim `WorkspacePage.jsx` (530) — extract papers model + dialogs + ingest wiring
- **Area:** [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx), [`WorkspacePage/WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx), [`WorkspacePage/WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx)
- **Issue:** После Wave I split осталась оркестрация: URL/meta workspace, work ids, `useJobStream` для ingest, paper cards, дедуп, summary/idea-диалоги. Размер 530 строк, риск регрессий при добавлении hypothesis диалога и новых ingest-сценариев (Wave K2 batch, Wave W actor).
- **Proposal:** Вынести `useWorkspacePapersModel` (works + meta + sort/filter), `WorkspaceDialogs` (summary, hypothesis, idea-assist), оставить в `WorkspacePage` только URL state + composition.
- **Acceptance:** `WorkspacePage.jsx` <= 280 строк; `npm run lint` / `npm run test` зелёные.
- **Synergy:** разблокирует UI-стороны **Wave S** (hypothesis modal) и расширения **Wave L** (smart dedup) без раздувания shell.
- **Raised:** 2026-04-25

### [OPEN] Split `ReaderWorkBody.jsx` (485) — chunks list + formatters + claims linking
- **Area:** [`ReaderWorkBody.jsx`](../../ui/src/components/work/ReaderWorkBody.jsx), [`ReaderClaimsPanel.jsx`](../../ui/src/components/work/ReaderClaimsPanel.jsx), [`PdfViewer.jsx`](../../ui/src/components/work/PdfViewer.jsx)
- **Issue:** Чанки + подсветка + сворачивания + ссылки в graph/ask + слайс `0..4000` в JSX; рост ожидается под Wave O (claims в Reader) и Wave M (страница PDF из цитаты, Wave K2.5).
- **Proposal:** `useReaderChunksState`, `ReaderChunkList`, `readerFormatters.js`; интеграцию с `ReaderClaimsPanel` оставить через композицию.
- **Acceptance:** `ReaderWorkBody.jsx` <= 280 строк; форматтеры покрыты юнитами.
- **Synergy:** **Wave O** (claims production) — UI claims в Reader; **Wave Q/R** (multi-hop, agent answer trace) — кросс-ссылки на работу.
- **Raised:** 2026-04-25

### [OPEN] Split `BenchmarkPage/CompareTab.jsx` (417) and `RunTab.jsx` (365)
- **Area:** [`BenchmarkPage/CompareTab.jsx`](../../ui/src/pages/BenchmarkPage/CompareTab.jsx), [`BenchmarkPage/RunTab.jsx`](../../ui/src/pages/BenchmarkPage/RunTab.jsx)
- **Issue:** Сравнение прогонов / запуск конфигурации — крупные tabs, контейнер логики.
- **Proposal:** Вынести `useCompareDeltas`, `DeltaTable`, `useRunLauncher`, `RunConfigForm`. Хранить metric formatting в общем хелпере.
- **Acceptance:** ни один таб > ≈250 строк.
- **Synergy:** Облегчит добавление UI для **Wave Q/R/P** ablation и judge-метрик.
- **Raised:** 2026-04-25

### [OPEN] Услoвный split `services/researchApi.js` (305) by domain modules
- **Area:** [`services/researchApi.js`](../../ui/src/services/researchApi.js)
- **Issue:** Текущий «один файл — все эндпоинты» (works, graph, ask, settings, agent, idea-assist) растёт линейно. После Wave Y3 добавится агент v2 SSE; после Wave T — больше dedup-эндпоинтов; после Wave M — judge-метрики.
- **Proposal:** Сегментировать на `services/research/{works,graph,ask,agent,ideaAssist,dedup,settings,benchmarks}.js`, оставить `services/researchApi.js` как barrel-export для обратной совместимости. `formatResearchApiError` — в `services/research/errors.js`.
- **Acceptance:** ни один сервис-модуль > ~150 строк; импорты в существующих компонентах продолжают работать через barrel-re-export.
- **Synergy:** **Wave Y3** (agent v2 SSE), **Wave T** (entity dedup), **Wave M/P** (judge endpoints).
- **Raised:** 2026-04-25

### [OPEN] i18n hardcoded copy: HypothesisPanel, IngestionSettings, Workspace dialogs
- **Area:** [`HypothesisPanel.jsx`](../../ui/src/components/work/HypothesisPanel.jsx), [`pages/SettingsPage/IngestionSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx), [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** В этих модулях встречаются хардкод-строки (`Generating...`, `No candidates`, `Workspace summary`, `Hypothesis / contradiction assist`, `Saving…`, `Save ingestion settings`) — расходится с [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md).
- **Proposal:** Вынести в i18n словари, добавить EN+RU ключи, заменить литералы на `t(...)`.
- **Acceptance:** ESLint i18n-проверка зелёная (если включена); ручной аудит не находит литералов в этих компонентах; `npm run lint` зелёный.
- **Raised:** 2026-04-25

### [OPEN] Switch dedup dialogs to `Cursor*` button family
- **Area:** [`WorkspacePage/WorkspaceDedupSection.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx), [`WorkDedupReviewDialog.jsx`](../../ui/src/components/graph/WorkDedupReviewDialog.jsx)
- **Issue:** Прямое использование MUI `Button` вместо `CursorButton` / `CursorPrimaryButton` / `CursorDangerButton` — расходится с дизайн-каноном (см. `.cursorrules` в osint-gr и общая дисциплина проекта).
- **Proposal:** Заменить импорты на `Cursor*` варианты из `components/common`; учесть варианты `contained/outlined/text`.
- **Acceptance:** ни один прямой импорт `@mui/material/Button` в `WorkspaceDedupSection`/`WorkDedupReviewDialog`; визуальный паритет с остальными dedup-кнопками; `npm run lint` зелёный.
- **Raised:** 2026-04-25

### [OPEN] Move `useScienceGraphForceSimulation.js` to `hooks/graph/`
- **Area:** [`components/graph/physics/useScienceGraphForceSimulation.js`](../../ui/src/components/graph/physics/useScienceGraphForceSimulation.js), [`hooks/`](../../ui/src/hooks/)
- **Issue:** ≈425 строк хука лежит в `components/graph/physics/`, рядом со «не-React» утилитами (quadTree, structuralCommunities). В `hooks/` сейчас только `useJobStream`/`usePollJob` — два «места» для сложной async-логики.
- **Proposal:** Перенести хук в `ui/src/hooks/graph/useScienceGraphForceSimulation.js` (или `hooks/useGraphSimulation.js`); оставить чистые модули physics в `components/graph/physics/`.
- **Acceptance:** импорт обновлён в `GraphCanvasMvp`; тесты симуляции зелёные.
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX1 layout & hero (закрывает H-WorkspacePageSlim)
- **Area:** [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx),
  [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx),
  [`WorkspacePaperList.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperList.jsx),
  [`WorkPaperCard.jsx`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx),
  новые `WorkspaceLayout.jsx`, `WorkspaceHero.jsx`, `WorkspaceSidePanel.jsx`
- **Issue:** На 1920px viewport контент `WorkspacePage` занимает ≤ 720px ширины
  (`WorkspaceIngestPanel` `maxWidth: 560`, `WorkPaperCard` `maxWidth: 720`), правые ~60% экрана пустые.
  «Активный workspace» виден только через `WorkspaceContextChip` 28×220px в правом верхнем углу shell-хедера —
  пользователь не понимает, в каком корпусе он работает и что куда грузится.
- **Proposal:** Убрать `maxWidth` из ingest-панели и карточек. `WorkspacePaperList` перевести на CSS grid
  `repeat(auto-fit, minmax(320px, 1fr))`. Двухколонный body через новый `WorkspaceLayout.jsx`
  (`grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr)` на md+; single column на xs/sm).
  Новый `WorkspaceHero.jsx` (90px, `FolderOpenOutlinedIcon` + h1 + counts/age + actions) заменяет блок `PageHeader`
  на этой странице. `WorkspaceSidePanel.jsx` — правая колонка (compact dedup queue + graph stats + recent activity).
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.1.
- **Acceptance:** На 1920×1080 контент использует ≥ 1280px (4 колонки карточек); на 1366×768 — 3 колонки;
  `WorkspaceHero` всегда виден над контентом; `WorkspacePage.jsx` ≤ 280 строк (закрывает существующий пункт
  `H-WorkspacePageSlim`); `npm run lint` / `npm run test` зелёные.
- **Synergy:** Закрывает пункт «Slim WorkspacePage.jsx (530)» выше; разблокирует Wave T UI (новые dedup-вкладки)
  и Wave S+ (hypothesis modal в side panel).
- **Raised:** 2026-04-25

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

### [OPEN] Frontend wiring for `/v2/agent/query` SSE (Wave Y3 follow-up)
- **Area:** [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx), [`hooks/useJobStream.js`](../../ui/src/hooks/useJobStream.js) (как референс), новый `hooks/useAgentStream.js`, `services/research/agent.js`
- **Issue:** Когда backend выкатит `/v2/agent/query` (SSE: `tool_call` / `tool_result` / `token` / `final_answer` / `error`), UI ещё на REST `/v1/agent/query`. Без отдельного refactor-пункта Wave Y6 не сможет удалить v1.
- **Proposal:** Хук `useAgentStream(query, ctx, { onEvent, onTerminal, fallbackPostMs })` поверх `EventSource`; интеграция в `useAskSubmit` (см. AskPanel decomposition); graceful fallback на v1.
- **Acceptance:** при `agent_runtime != "retrieval_v1"` UI открывает один SSE-стрим, рендерит инкрементальный tool trace и финальный ответ; lint/test зелёные.
- **Synergy:** **Wave Y3 → Y6** — необходимое условие удаления `POST /v1/agent/query`.
- **Raised:** 2026-04-25
