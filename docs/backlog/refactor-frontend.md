# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Queue

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

### [OPEN] Graph canvas — библиотека или углублённый порт osint-gr
- **Area:** `ui/src/components/graph/` (`GraphCanvasMvp.jsx`, `GraphWorkspacePanel.jsx`, `graphUiLimits.js`, `graphViewState.js`)
- **Issue:** raw HTML Canvas закрывает Phase 4.2–4.3; для force layout, мини-карты, сложных графов может понадобиться **React Flow / Sigma** или порт симуляции osint-gr без дублирования логики.
- **Proposal:** оценить после нагрузочного UX: маппинг из `normalizeGraphPayload` + `capGraphForUi`; не тащить OSINT context, DB save, чат. **Сводка osint-gr vs наш стек, parity Wave 3–4 и порядок Wave 4** — в [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) (разделы *Reference implementation*, *Parity vs osint-gr*, *Wave 4 roadmap*); итог layout-spike — [`docs/adr/006-graph-layout-stack-spike.md`](../adr/006-graph-layout-stack-spike.md).
- **Acceptance:** решение зафиксировано в PR/`graph-ui-plan.md`; при внедрении библиотеки — паритет: выбор узла/ребра, URL, `GraphDetailPanel`, лимиты UI.
- **Raised:** 2026-04-08
- **Note:** 4.1–4.4 + пост-4.4: `warnings`, `GraphCanvasMvp`, `graphUiLimits`, `graphCanvasTransform`, легенда, Graph Lab, автоцентр при смене выбора, Reset zoom, a11y карточек. **V1 layout зафиксирован** в [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) (круг + raw Canvas); следующий крупный шаг — **Wave 4.3** spike (см. ADR 006) только при продуктовой необходимости.

<!-- Example:
### [OPEN] Example — unify research API error handling
- **Area:** `ui/src/services/researchApi.js`, callers
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->
