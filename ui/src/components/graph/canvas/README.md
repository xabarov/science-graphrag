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

### Canvas input seam (`hooks/graphCanvasInput/`)

[`hooks/useGraphCanvasInput.js`](./hooks/useGraphCanvasInput.js) is a **facade** only: physics pointer bridge + shared drag refs + composition.

| Module | Responsibility |
| --- | --- |
| [`hooks/graphCanvasInput/hoverPick.js`](./hooks/graphCanvasInput/hoverPick.js) | `useGraphCanvasInputHoverPick` — hover/edge cursor state, RAF-coalesced `queueHoverPick` (skips while pan/node drag is **active+moved**); cancels pending RAF on unmount. |
| [`hooks/graphCanvasInput/pointerDown.js`](./hooks/graphCanvasInput/pointerDown.js) | Primary-button down: `dispatchGraphCanvasPointerDown`, node-drag vs pan session start, circle→force `flushSync` when hitting a node. |
| [`hooks/graphCanvasInput/pointerMove.js`](./hooks/graphCanvasInput/pointerMove.js) | Node-drag move (physics reheat on first threshold crossing), pan translate, else delegate to `queueHoverPick`. |
| [`hooks/graphCanvasInput/pointerUp.js`](./hooks/graphCanvasInput/pointerUp.js) | Release capture, pin-on-drop policy, `dispatchGraphCanvasPointerUp` in `finally`, click vs drag end paths. |
| [`hooks/graphCanvasInput/clickSelection.js`](./hooks/graphCanvasInput/clickSelection.js) | `resolveGraphCanvasClickSelection` — hit-test for tap after pan-without-move (node / edge / canvas). |
| [`hooks/graphCanvasInput/hitTestContext.js`](./hooks/graphCanvasInput/hitTestContext.js) | `buildNodeHitTestScreenOpts` — shared opts for `hitTestNodeScreen` (label bridge via `activeForLabelSetRef`). |
| [`hooks/graphCanvasInput/constants.js`](./hooks/graphCanvasInput/constants.js) | `DRAG_THRESHOLD_PX` for pan and node-drag. |

**Ownership:** pointer session state lives in `dragRef` / `nodeDragRef` on the facade; hover ids live inside `useGraphCanvasInputHoverPick`. Controller must keep passing `activeForLabelSetRef` so hit-tests read the freshest label set without an extra render cycle (same contract as before the split). [`GraphCanvasMvp.jsx`](./GraphCanvasMvp.jsx) wires `onPointerCancel` to the same handler as `onPointerUp` so cancel ends capture and runs `dispatchGraphCanvasPointerUp` in `finally`.

Rendering pipeline: [`graphCanvasMvpFrame.js`](./graphCanvasMvpFrame.js) + [`graphCanvasDraw.js`](./graphCanvasDraw.js) (facade to [`draw/`](./draw/)).

Force integrator hook: [`../../../hooks/graph/useScienceGraphForceSimulation.js`](../../../hooks/graph/useScienceGraphForceSimulation.js) — RAF lifecycle; delegates to:

- [`../../../hooks/graph/scienceGraphSimulationResetPolicy.js`](../../../hooks/graph/scienceGraphSimulationResetPolicy.js) — repulsion / topology / epoch resets
- [`../../../hooks/graph/scienceGraphSimulationGraphPrep.js`](../../../hooks/graph/scienceGraphSimulationGraphPrep.js) — per-run link/type/community maps
- [`../../../hooks/graph/scienceGraphSimulationTickEngine.js`](../../../hooks/graph/scienceGraphSimulationTickEngine.js) — one physics step (`createRunOnePhysicsTick`)

Do not reintroduce ad-hoc physics pause toggles here; use [`../../../hooks/graph/useGraphPhysicsPolicy.js`](../../../hooks/graph/useGraphPhysicsPolicy.js).

## See also

- Workspace / flow / detail shell (cards vs React Flow vs canvas wiring): [`../workspace/README.md`](../workspace/README.md).
