# Graph canvas (MVP) — module seams

Thin UI shell: [`GraphCanvasMvp.jsx`](./GraphCanvasMvp.jsx) — theme/i18n, empty state, composes toolbar + canvas + legends.

Orchestration: [`hooks/useGraphCanvasMvpController.js`](./hooks/useGraphCanvasMvpController.js) — composes the hooks below; owns shared refs (`canvasRef`, `positionsRef`, pin/drag refs), i18n callbacks, `invokeCanvasRedrawRef` bridge (physics/input must call a stable repaint; the ref is assigned in paint controller’s `useLayoutEffect`).

Sub-orchestration (same folder):

- [`hooks/useGraphCanvasWorldPositions.js`](./hooks/useGraphCanvasWorldPositions.js) — `useGraphCanvasWorldPositions`: `layoutWorldRadius`, simulation buffers, and `getPositionsForFrame` (safe before viewport). `useGraphCanvasWorldSimulationLifecycle`: `useScienceGraphForceSimulation` then `useGraphCanvasTopologyReseed` (same order as historical wiring; needs `applyFit` + `canvasSize` from viewport).
- [`hooks/graphCanvasMvpDerivedModel.js`](./hooks/graphCanvasMvpDerivedModel.js) — memoized topology/signature/repulsion/search/community/edge-legend derived state (no side effects).
- [`hooks/graphCanvasMvpNodeClickRouting.js`](./hooks/graphCanvasMvpNodeClickRouting.js) — pure `routeGraphCanvasNodeClick` (Aggregator expand vs `onSelectNode`).
- [`hooks/useGraphCanvasMvpViewActions.js`](./hooks/useGraphCanvasMvpViewActions.js) — fit/restart/unpin/center/double-click, view presets, dense-label hint persistence.
- [`hooks/useGraphCanvasNodeContextMenu.js`](./hooks/useGraphCanvasNodeContextMenu.js) — context menu open/close + node hit-test.
- [`hooks/useGraphCanvasPaintController.js`](./hooks/useGraphCanvasPaintController.js) — `paintGraphCanvasMvpFrame` assembly + ref bridge + repaint on `transform`.

Also composed from existing hooks: [`hooks/useGraphCanvasViewport.js`](./hooks/useGraphCanvasViewport.js), [`hooks/useGraphCanvasInput.js`](./hooks/useGraphCanvasInput.js), [`hooks/useGraphCanvasWheelZoom.js`](./hooks/useGraphCanvasWheelZoom.js), [`hooks/useCanvasLabelMode.js`](./hooks/useCanvasLabelMode.js).

Rendering pipeline: [`graphCanvasMvpFrame.js`](./graphCanvasMvpFrame.js) + [`graphCanvasDraw.js`](./graphCanvasDraw.js) (facade to [`draw/`](./draw/)).

Force integrator hook: [`../../../hooks/graph/useScienceGraphForceSimulation.js`](../../../hooks/graph/useScienceGraphForceSimulation.js) — RAF lifecycle; delegates to:

- [`../../../hooks/graph/scienceGraphSimulationResetPolicy.js`](../../../hooks/graph/scienceGraphSimulationResetPolicy.js) — repulsion / topology / epoch resets
- [`../../../hooks/graph/scienceGraphSimulationGraphPrep.js`](../../../hooks/graph/scienceGraphSimulationGraphPrep.js) — per-run link/type/community maps
- [`../../../hooks/graph/scienceGraphSimulationTickEngine.js`](../../../hooks/graph/scienceGraphSimulationTickEngine.js) — one physics step (`createRunOnePhysicsTick`)

Do not reintroduce ad-hoc physics pause toggles here; use [`../../../hooks/graph/useGraphPhysicsPolicy.js`](../../../hooks/graph/useGraphPhysicsPolicy.js).
