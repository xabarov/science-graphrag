# Graph workspace shell — module seams

Orchestrates **data target**, **toolbar + legend**, **visualization mode** (cards / React Flow / canvas), **detail side panel**, **layer counts footer**, and **debug inspector**. Canvas physics, pointer input, and draw pipeline stay under [`../canvas/README.md`](../canvas/README.md).

## Layout ownership

| Layer | Responsibility |
| --- | --- |
| [`GraphWorkspacePanel.jsx`](./GraphWorkspacePanel.jsx) | Composes hooks + sections; title/subtitle; loading/error/empty chrome; trace context banner inputs. |
| [`hooks/useGraphWorkspacePanelState.js`](./hooks/useGraphWorkspacePanelState.js) | Local UI state + `localStorage` sync (viz mode, layout, legend, details, find query, canvas color/hulls, center-on-node requests). |
| [`hooks/useGraphWorkspacePanelActions.js`](./hooks/useGraphWorkspacePanelActions.js) | Selection handlers, open-details-on-select, local-find “focus first match”, graph color-by side effects. |
| [`hooks/useGraphWorkspacePanelCommunityMap.js`](./hooks/useGraphWorkspacePanelCommunityMap.js) | UI community map for hulls/legend from `displayGraph` topology. |
| [`hooks/useGraphWorkspaceData.js`](./hooks/useGraphWorkspaceData.js) | Workspace graph fetch, visibility, stats, neighbor/aggregator expansion. |
| [`hooks/useGraphWorkspaceProjection.js`](./hooks/useGraphWorkspaceProjection.js) | Projected/visible/display graph + inspector model + search match ids. |
| [`sections/GraphWorkspaceMainSection.jsx`](./sections/GraphWorkspaceMainSection.jsx) | Grid: `GraphVisualization` \| `GraphFlowView` \| `GraphPhysicsPointerBridgeProvider` + `GraphCanvasMvp` + `GraphSidePanel`. |
| [`sections/GraphWorkspaceAlertsAboveMainGrid.jsx`](./sections/GraphWorkspaceAlertsAboveMainGrid.jsx) | Normalized payload + large-payload performance alerts. |
| [`sections/GraphWorkspaceAlertsBelowFooter.jsx`](./sections/GraphWorkspaceAlertsBelowFooter.jsx) | Traceability + empty-graph alerts after footer. |
| [`sections/GraphWorkspaceDebugInspectorSection.jsx`](./sections/GraphWorkspaceDebugInspectorSection.jsx) | Thin wrapper around `GraphDebugInspector`. |
| [`WorkspaceGraphToolbar.jsx`](./WorkspaceGraphToolbar.jsx) | Toolbar shell; sub-rows in `WorkspaceToolbar*`, model in [`workspaceToolbarModel.js`](./workspaceToolbarModel.js). |

## React Flow (flow mode)

| Module | Responsibility |
| --- | --- |
| [`../flow/GraphFlowView.jsx`](../flow/GraphFlowView.jsx) | Empty-state guard + `ReactFlowProvider` + inner shell. |
| [`../flow/GraphFlowInner.jsx`](../flow/GraphFlowInner.jsx) | Wires i18n edge labels, `useGraphFlowState`, `useGraphFlowSelectionHandlers`, toolbar + viewport. |
| [`../flow/hooks/useGraphFlowState.js`](../flow/hooks/useGraphFlowState.js) | Nodes/edges sync, minimap preference, `fitView` on layout signature + telemetry. |
| [`../flow/hooks/useGraphFlowSelectionHandlers.js`](../flow/hooks/useGraphFlowSelectionHandlers.js) | Click/pane/Escape selection + toolbar view actions. |
| [`../flow/GraphFlowViewport.jsx`](../flow/GraphFlowViewport.jsx) | `ReactFlow` + `Background` / `Controls` / `MiniMap`. |
| [`../flow/GraphFlowToolbar.jsx`](../flow/GraphFlowToolbar.jsx) | Fit / reset zoom / center / minimap toggle. |
| [`../flow/graphFlowConstants.js`](../flow/graphFlowConstants.js) | Min height + minimap LS key helpers. |
| [`../flow/graphFlowNodeTypes.js`](../flow/graphFlowNodeTypes.js) | `nodeTypes` map for React Flow (keeps custom node in a component-only module). |

## Node detail (side panel body)

| Module | Responsibility |
| --- | --- |
| [`../shell/detail/GraphNodeDetailSection.jsx`](../shell/detail/GraphNodeDetailSection.jsx) | Computes claim/method/property entries; orders sections. |
| [`../shell/detail/graphNodeDetailSectionSx.js`](../shell/detail/graphNodeDetailSectionSx.js) | Shared `sx` builders (bordered panels, code `<pre>`). |
| [`../shell/detail/detailSections/*`](../shell/detail/detailSections/) | Aggregator, default header, work membership, author works, claim, method, properties, connections, raw JSON. |

## Boundaries (do not blur)

- **Workspace** must not reimplement canvas pointer/hit-test/draw; delegate to `GraphCanvasMvp` + [`useGraphCanvasMvpController`](../canvas/hooks/useGraphCanvasMvpController.js).
- **Flow** must not own workspace visibility or projection; it receives `displayGraph` + resolved selection ids from the workspace panel.
- **Detail** sections are presentation + light formatting; heavy field logic stays in [`detailFormatters.js`](../shell/detail/detailFormatters.js) / localize helpers.
