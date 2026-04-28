# ADR 006: Graph layout stack — time-boxed spike (Wave 4.3)

- **Status:** Accepted (library POC merged; force/osint path still optional)
- **Date:** 2026-04-08

## Status update (execution)

- **2026-04-08 (initial):** No React Flow / Sigma / force-simulation POC was merged; v1 remained circle Canvas only.
- **2026-04-08 (decision):** **React Flow** POC merged: optional third viz mode **Flow** in [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx), fed from `normalizeGraphPayload` / `capGraphForUi` via [`graphFlowAdapter.js`](../../ui/src/components/graph/flow/graphFlowAdapter.js) and [`GraphFlowView.jsx`](../../ui/src/components/graph/flow/GraphFlowView.jsx). Initial node positions reuse the same **circle world layout** as Canvas (`computeWorldLayout`); **no** force-directed simulation, **no** OSINT clustering. Default UX remains **Cards** / **Graph** (Canvas). Further options (Sigma, osint `useForceSimulation` port, iterative physics) stay backlog — see [`refactor-frontend.md`](../backlog/refactor-frontend.md).
- **2026-04-08 (Phase C):** Optional **MiniMap** + toggle added to Flow (not part of the original spike merge scope; see *Layout stack* Phase C in [`graph-ui-plan.md`](../specs/graph-ui-plan.md)).
- **2026-04-08 (Canvas force):** Optional **Force** mode on the HTML Canvas (see [`007-canvas-force-layout-port.md`](./007-canvas-force-layout-port.md)) — osint-style simulation port without OSINT domain hooks; React Flow remains non-force.

## Context

The shipped v1 graph UI uses a **deterministic circle layout** ([`graphCanvasTransform.js`](../../ui/src/components/graph/canvas/graphCanvasTransform.js)) and raw Canvas ([`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx)). The reference project **osint-gr** uses a **custom force simulation** with optional **QuadTree** repulsion and **clustering** hints (see [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md), *Parity vs osint-gr*).

Dense or growing 1-hop neighborhoods may need a different layout or library without breaking the normalized API contract.

## Decision (spike scope)

Run a **time-boxed spike** (suggested 1–3 days) to evaluate **one** of:

1. **Library POC:** React Flow or Sigma.js fed from `normalizeGraphPayload` / `capGraphForUi` (read-only).
2. **Code port POC:** Subset of osint-gr `useForceSimulation` + `quadTree` **without** OSINT-specific clustering (`personId`, community detection can stay off or be replaced by a stub).

**Out of scope for the spike merge:** minimap, full clustering parity, workspace/chat integration.

## Consequences

- **Contract:** Keep [`normalizeGraphPayload`](../../ui/src/components/graph/model/graphViewState.js), URL/trace params for node/edge selection, and [`GraphDetailPanel`](../../ui/src/components/graph/shell/GraphDetailPanel.jsx) behavior aligned with the chosen surface.
- **Documentation:** Update [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) *Layout stack v1* with the spike outcome; set this ADR to **Accepted** or **Superseded** when a product decision is made.
- **Default if spike slips:** Remain on circle Canvas until product priority changes.

## Execution checklist (when product prioritizes this spike)

1. **Time-box** (e.g. 1–3 days) and pick **one** path: library POC **or** force/QuadTree port (see *Decision* above).
2. **Branch:** feed the UI only from `normalizeGraphPayload` + `capGraphForUi`; no new API fields without contract update.
3. **Parity:** node + edge selection, URL sync (`traceabilityState`), `GraphDetailPanel`, `GRAPH_UI_MAX_*` caps — must behave or gaps documented.
4. **Docs:** update *Layout stack v1* in [`graph-ui-plan.md`](../specs/graph-ui-plan.md); set this ADR to **Accepted** or **Superseded** with outcome summary.
5. **Backlog:** close or narrow [`refactor-frontend.md`](../backlog/refactor-frontend.md) **[OPEN] Graph canvas** when the product decision is recorded (library chosen, or explicitly defer again).

## References

- Backlog: [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) — [OPEN] Graph canvas
- Osint paths: `osint-gr/frontend/src/components/features/GraphVisualization.jsx`, `graphVisualization/hooks/useForceSimulation.js`, `utils/quadTree.js`
