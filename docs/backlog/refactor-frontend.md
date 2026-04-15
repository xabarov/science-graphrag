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

### [OPEN] Graph canvas — Neo4j Browser–grade UX (optional)
- **Area:** `GraphCanvasMvp.jsx`, при необходимости отдельный hook
- **Issue:** Сделано: force restart, unpin, +/- / 0 keyboard zoom/fit, tooltips. В Neo4j Browser ещё есть command bar, стили рёбер по типу, инспектор запросов, контекстное меню, экспорт — не требуются для read-only neighborhood v1.
- **Proposal:** По продукту — контекстное меню узла, легенда типов рёбер на canvas, double-click fit selection; не раздувать MVP без запроса.
- **Acceptance:** N/A до приоритизации.
- **Raised:** 2026-04-08
