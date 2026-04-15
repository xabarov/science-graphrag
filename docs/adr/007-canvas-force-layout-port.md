# ADR 007: Canvas force layout (osint-gr simulation port)

- **Status:** Accepted
- **Date:** 2026-04-08

## Context

ADR 006 recorded the **React Flow** POC and left **force-directed** physics as optional follow-up. The product asked for a **Circle | Force** toggle on the existing **Canvas** (`GraphCanvasMvp`) without a fourth top-level viz tab, reusing the normalized API and UI caps.

## Decision

- Port a **subset** of osint-gr’s custom simulation: **Barnes–Hut** repulsion (`QuadTree`), link springs, cooling, soft bounds, optional **structural** label-propagation communities — **without** OSINT domain types (`personId`, `HAS_ORGANIZATIONS`, etc.).
- **Seed** positions with the same **`computeWorldLayout`** / `worldRadiusForNodeCount` as **Circle** so Circle ↔ Force does not start from a blank layout.
- **Topology signature:** `getGraphLayoutSignature` — reinitialize simulation when node/edge sets change; do not reset on selection-only changes.
- **UX:** `GraphWorkspacePanel` exposes **Circle | Force** when **Graph** is selected; `localStorage` key `graphCanvasLayoutMode`. Canvas toolbar adds **repulsion** slider; `graphCanvasRepulsionPercent` persists strength.
- **Pointer:** distinguish **node drag** vs **pan**; optional **pin** after drag when the layout is stable (`fixedNodesRef`), matching osint behavior in spirit.
- **Follow-up UX (same ADR scope):** **Restart sim** re-seeds with `jitterWorld` + `simulationSignature` bump so cooling resets without graph change; **Unpin all** clears pinned nodes and resumes motion; keyboard **`+` / `−` / `0`** (zoom / fit) when the graph region is focused — Neo4j Browser–like ergonomics without a command bar.

## Consequences

- New modules under `ui/src/components/graph/physics/` and `graphSimulationAdapter.js`; `GraphCanvasMvp` accepts `layoutMode: "circle" | "force"`.
- **No API change** — still `normalizeGraphPayload` + `capGraphForUi`; selection, URL trace, `GraphDetailPanel` unchanged.
- Flow mode remains **non–force-directed** (out of scope for this ADR).

## References

- Spec: [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) *Layout stack*
- ADR 006: [`006-graph-layout-stack-spike.md`](./006-graph-layout-stack-spike.md)
