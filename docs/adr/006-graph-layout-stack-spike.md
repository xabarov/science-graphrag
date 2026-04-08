# ADR 006: Graph layout stack — time-boxed spike (Wave 4.3)

- **Status:** Proposed
- **Date:** 2026-04-08

## Context

The shipped v1 graph UI uses a **deterministic circle layout** ([`graphCanvasTransform.js`](../../ui/src/components/graph/graphCanvasTransform.js)) and raw Canvas ([`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx)). The reference project **osint-gr** uses a **custom force simulation** with optional **QuadTree** repulsion and **clustering** hints (see [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md), *Parity vs osint-gr*).

Dense or growing 1-hop neighborhoods may need a different layout or library without breaking the normalized API contract.

## Decision (spike scope)

Run a **time-boxed spike** (suggested 1–3 days) to evaluate **one** of:

1. **Library POC:** React Flow or Sigma.js fed from `normalizeGraphPayload` / `capGraphForUi` (read-only).
2. **Code port POC:** Subset of osint-gr `useForceSimulation` + `quadTree` **without** OSINT-specific clustering (`personId`, community detection can stay off or be replaced by a stub).

**Out of scope for the spike merge:** minimap, full clustering parity, workspace/chat integration.

## Consequences

- **Contract:** Keep [`normalizeGraphPayload`](../../ui/src/components/graph/graphViewState.js), URL/trace params for node/edge selection, and [`GraphDetailPanel`](../../ui/src/components/graph/GraphDetailPanel.jsx) behavior aligned with the chosen surface.
- **Documentation:** Update [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) *Layout stack v1* with the spike outcome; set this ADR to **Accepted** or **Superseded** when a product decision is made.
- **Default if spike slips:** Remain on circle Canvas until product priority changes.

## References

- Backlog: [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) — [OPEN] Graph canvas
- Osint paths: `osint-gr/frontend/src/components/features/GraphVisualization.jsx`, `graphVisualization/hooks/useForceSimulation.js`, `utils/quadTree.js`
