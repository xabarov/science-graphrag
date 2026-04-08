# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Queue

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
