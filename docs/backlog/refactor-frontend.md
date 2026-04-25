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

### [OPEN] Graph canvas — split `GraphCanvasMvp` (input vs physics vs draw)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx)
- **Issue:** Файл ~1000+ строк: pointer/transform, wiring симуляции и отрисовка canvas в одном модуле; после force/reheat правок рост риска регрессий.
- **Proposal:** Вынести pointer/pan/drag/select в `useGraphCanvasInput` (или модуль рядом), fit/transform в утилиту/hook, оставить в компоненте только glue + `draw` либо `graphCanvasDraw.js`.
- **Acceptance:** оркестратор canvas без «god file» (heuristic: &lt;400 строк или явно разделённые слои); поведение drag/pan/force без регрессий; `npm run lint` / `npm run test` зелёные.
- **Raised:** 2026-04-19

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

### [OPEN] Frontend wiring for `/v2/agent/query` SSE (Wave Y3 follow-up)
- **Area:** [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx), [`hooks/useJobStream.js`](../../ui/src/hooks/useJobStream.js) (как референс), новый `hooks/useAgentStream.js`, `services/research/agent.js`
- **Issue:** Когда backend выкатит `/v2/agent/query` (SSE: `tool_call` / `tool_result` / `token` / `final_answer` / `error`), UI ещё на REST `/v1/agent/query`. Без отдельного refactor-пункта Wave Y6 не сможет удалить v1.
- **Proposal:** Хук `useAgentStream(query, ctx, { onEvent, onTerminal, fallbackPostMs })` поверх `EventSource`; интеграция в `useAskSubmit` (см. AskPanel decomposition); graceful fallback на v1.
- **Acceptance:** при `agent_runtime != "retrieval_v1"` UI открывает один SSE-стрим, рендерит инкрементальный tool trace и финальный ответ; lint/test зелёные.
- **Synergy:** **Wave Y3 → Y6** — необходимое условие удаления `POST /v1/agent/query`.
- **Raised:** 2026-04-25
