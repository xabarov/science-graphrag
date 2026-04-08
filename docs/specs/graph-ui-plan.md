# Graph UI plan (science-graphrag)

Companion to **Phase 4** in [`ui-ux-master-plan.md`](./ui-ux-master-plan.md). This doc fixes the **API ↔ UI contract** and targets for canvas work (Phases 4.1–4.4).

## Scope

- **In scope:** read-only visualization of `GET /v1/works/{work_id}/graph`, selection + detail panel, URL/trace sync, empty/loading/error, performance limits.
- **Out of scope (for now):** mutating Neo4j from the UI, OSINT-style chat, case/workspace contexts from osint-gr.

## Backend contract

**Endpoint:** `GET /v1/works/{work_id}/graph`  
**Implementation:** [`science_graphrag/api/works.py`](../../science_graphrag/api/works.py) — `work_graph_neighborhood`.

Response shape (conceptual):

| Field | Type | Notes |
|-------|------|--------|
| `work_id` | string | Center work |
| `nodes` | array | Each: `id`, `type`, `label` (and optional extra fields preserved in `raw` after normalize) |
| `edges` | array | Each: `source`, `target`, `type` (relationship type); orientation matches Neo4j (`startNode`→`source`, `endNode`→`target`); may omit `id` (UI synthesizes) |
| `meta` | object | e.g. `semantic_available` |

**Server limit:** neighborhood query caps at **200** adjacent rows; additional **client caps** for rendering are `GRAPH_UI_MAX_NODES` / `GRAPH_UI_MAX_EDGES` in [`graphUiLimits.js`](../../ui/src/components/graph/graphUiLimits.js).

## Normalized UI model

**Code:** [`ui/src/components/graph/graphViewState.js`](../../ui/src/components/graph/graphViewState.js) — `normalizeGraphPayload`, `resolveSelectedNodeId`, `deriveGraphDetail`.

After normalization:

- **Node:** `{ id, label, type, raw }`
- **Edge:** `{ id, source, target, type, raw }`
- **Graph:** `{ workId, nodes, edges, meta, nodeCount, edgeCount, selectedNodeId, warnings }`

**Duplicate `node.id`:** The first occurrence keeps the original string; later duplicates get deterministic ids `originalId__dup1`, `originalId__dup2`, … so selection and edges stay referencable. A human-readable message is appended to `warnings` for each reassignment.

**Orphan edges:** Edges whose `source` or `target` is not in the set of normalized node ids are **dropped** (not rendered). A single summary line is added to `warnings` with the drop count.

**Empty graph:** `warnings` may be empty; `nodeCount` / `edgeCount` reflect the final arrays after the rules above.

**Adapter:** [`ui/src/components/graph/graphAdapter.js`](../../ui/src/components/graph/graphAdapter.js) — `fetchWorkGraphNormalized(workId)` wraps the API and `normalizeGraphPayload`.

### Canvas target model (Phase 4.2+)

Any canvas or graph library should consume the **normalized** graph (or a thin mapper from it):

- **Nodes** need stable `id` for selection and URL round-trip.
- **Edges** need `source` / `target` referencing node `id`s (directed as in Neo4j); orphan edges are **filtered** in `normalizeGraphPayload` and summarized in `warnings` (not only dev logs).
- **Layout:** initial positions can be random or circular; force simulation (see osint-gr) or library layout fills `x`, `y` in an internal structure — do not persist layout to API unless product requires it.

### URL and traceability

- **Standalone:** [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) — `work_id`, optional trace params via [`traceabilityState.js`](../../ui/src/components/work/traceabilityState.js).
- **Selection:** `selectedNodeId` (or `node_id` in URL where applicable) must resolve with `resolveSelectedNodeId` so deep links never point to a missing id silently without fallback.

## UI composition (current)

| Piece | File | Role |
|-------|------|------|
| Shell | `GraphWorkspacePanel.jsx` | Load graph, Cards/Graph toggle, normalization + UI-cap alerts, grid + detail |
| List view | `GraphVisualization.jsx` | Phase 4 **v0** — card grid |
| Canvas | `GraphCanvasMvp.jsx` | HTML Canvas: zoom/pan, fit / center / reset zoom, Escape; node + edge hover highlight + cursor; directed edges (arrow at `target`); labels on nodes and edges |
| Limits | `graphUiLimits.js` | `capGraphForUi` (`GRAPH_UI_MAX_*`); chips show full API counts |
| Legend | `GraphTypeLegend.jsx`, `graphTypeLegend.js` | Unique `node.type` / `edge.type` chips from `displayGraph` |
| Shell states | `graphShellStates.jsx` | Shared empty / loading / error patterns (Graph page, tab, panel) |
| Canvas math | `graphCanvasTransform.js` | World layout + fit + screen/world mapping; `worldRadiusForNodeCount(n)` grows the circle when many nodes reduce chord spacing |
| Canvas styles | `graphCanvasStyle.js` | Node type colors, hover stroke, truncated node/edge labels on canvas |
| Details | `GraphDetailPanel.jsx` | Edges + raw JSON (`deriveGraphDetail` on **full** graph) |
| Data | `graphAdapter.js`, `graphViewState.js` | Fetch + normalize + derive |

**Modes:** **Cards** vs **Graph** share capped `displayGraph`; detail panel uses the full normalized graph.

### Phase 4.2 stack decision (spike)

**Chosen for the in-repo spike:** lightweight **HTML Canvas** view (`GraphCanvasMvp.jsx`) — no extra npm dependency, circle layout, click-to-select wired to the same `selectedNodeId` / `deriveGraphDetail` as the card grid. **Optional later:** evaluate **React Flow / Sigma** or a **port of osint-gr** patterns for force layout or very large graphs.

### Phase 4.3 (navigation and resilience)

- **Canvas:** wheel zoom (cursor anchor), drag-to-pan, **Fit**, **Center on selected**; world-space positions; focusable region; **Escape** clears selection (URL drops `node` via `buildTraceabilityParams` when `nodeId` is empty).
- **UI caps:** `GRAPH_UI_MAX_NODES` / `GRAPH_UI_MAX_EDGES` in `graphUiLimits.js`; selected node kept visible when possible; Alert when caps apply (separate from normalization `warnings`).
- **Layout:** `minHeight` + stretched columns in `GraphWorkspacePanel` (aligned with osint-gr visualization section idea).

### Phase 4.4 (polish and Graph Lab)

- **Shared states:** [`graphShellStates.jsx`](../../ui/src/components/graph/graphShellStates.jsx) — consistent empty/loading/error copy and styles for [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx), [`GraphTab.jsx`](../../ui/src/pages/WorkspacePage/tabs/GraphTab.jsx), and the panel.
- **Legend:** [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx) under the Cards/Graph toggle.
- **Graph Lab:** query flag `lab=1` on `/graph` or workspace graph tab — diagnostics JSON expanded by default; otherwise hidden behind **Show diagnostics** (`Collapse`).
- **Layout source of truth:** circle positions and fit/zoom math live in [`graphCanvasTransform.js`](../../ui/src/components/graph/graphCanvasTransform.js) (used by `GraphCanvasMvp`); unit tests in `graphCanvasTransform.test.js`. Ring **radius scales with node count** (`worldRadiusForNodeCount`) so dense 1-hop neighborhoods stay readable after **Fit**.

### Post–4.4 behavior (canvas + cards)

- **Canvas:** changing selection does **not** auto-pan the viewport (avoids fighting user pan/zoom). **Fit** refits the full graph after load or graph change; **Center on selected** pans to the current node at the same zoom; **Reset zoom** sets scale to `1` keeping the world point under the viewport center fixed. The displayed node set changing (new `work_id` / normalized graph) runs **Fit** again via layout effect.
- **Cards:** [`GraphVisualization.jsx`](../../ui/src/components/graph/GraphVisualization.jsx) uses **roving `tabIndex`**: one card is tab-focusable at a time; **Arrow** keys move focus and update selection; **Enter** / **Space** activate the focused card.
- **Responsive / a11y slice:** [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx) stacks the graph + detail columns on narrow viewports (`xs` single column, `md` two columns). [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx) exposes a visually hidden **`aria-live="polite"`** line for the current selection and an **`aria-label`** on the canvas element.
- **Further narrow-view polish:** [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx) uses slightly reduced padding and label size on `xs`. Benchmark **Case** / **Results** dialogs ([`CaseDetailDialog.jsx`](../../ui/src/pages/BenchmarkPage/CaseDetailDialog.jsx), [`ResultsDialog.jsx`](../../ui/src/pages/BenchmarkPage/ResultsDialog.jsx)) use MUI **`fullScreen`** below the `sm` breakpoint.

### Phase 4 completion (product)

For **Phase 4 UI**, the shipped **v1** (circle layout + raw Canvas, ADR above) meets acceptance: read-only neighborhood graph, cards/canvas, URL-driven selection, limits, Graph Lab, post-4.4 hardening (checklist). **Force-directed layout, graph npm libraries, or an osint-gr simulation port** are **not** required to call Phase 4 done; they remain **backlog / optional spike** ([`refactor-frontend.md`](../backlog/refactor-frontend.md)).

### Layout stack v1 (product decision)

- **Shipped v1:** deterministic **circle layout** with **adaptive world radius** in [`graphCanvasTransform.js`](../../ui/src/components/graph/graphCanvasTransform.js) + raw **Canvas** in `GraphCanvasMvp` — no graph npm dependency, predictable for neighborhood size; on-canvas **type-colored nodes**, **hover** highlight, **truncated labels** for nodes and edge types ([`graphCanvasStyle.js`](../../ui/src/components/graph/graphCanvasStyle.js)).
- **When to revisit:** need force-directed layout, minimap, or very dense graphs → time-boxed spike **React Flow / Sigma** or read-only port of osint-gr `useForceSimulation` / `GraphVisualization` hooks; keep `normalizeGraphPayload`, `capGraphForUi`, URL selection, and `GraphDetailPanel` as the contract.

## Reference implementation (osint-gr)

Use for **patterns**, not copy-paste of product logic:

| Topic | Path (repo `osint-gr`) |
|-------|-------------------------|
| Page shell | `frontend/src/pages/KnowledgeGraphPage.jsx` |
| Layout split | `frontend/src/pages/KnowledgeGraphPage/components/KnowledgeGraphVisualizationSection.jsx` |
| Canvas + simulation | `frontend/src/components/features/GraphVisualization.jsx` |
| Hooks | `frontend/src/components/features/graphVisualization/hooks/*` |
| Toolbar pattern | `frontend/src/components/features/graphVisualization/components/GraphControls.jsx` |

## Phased delivery (mirror master plan)

1. **4.1** — Document and test edge cases on normalized model; align with this spec.
2. **4.2** — Canvas MVP + selection ↔ detail panel.
3. **4.3** — Zoom/pan, fit, limits, keyboard — **done** in `GraphCanvasMvp.jsx`, `graphUiLimits.js`, `GraphWorkspacePanel.jsx`.
4. **4.4** — Polish, legend, Graph Lab flag — **done** (see Phase 4.4 above).

## Checklist (acceptance)

- [x] Normalized graph from live API renders without console errors for empty / single Work / full neighborhood (regression: run UI manually).
- [x] Selected node matches `deriveGraphDetail` and URL when trace params present.
- [x] Canvas shows **edges** as lines (or library equivalent), not only nodes.
- [x] Behavior documented when `nodeCount` or `edgeCount` exceeds UI threshold (`capGraphForUi` + Alert; see `GRAPH_UI_MAX_NODES` / `GRAPH_UI_MAX_EDGES`).
- [x] Type legend and Graph Lab (`?lab=1`) / collapsed diagnostics; shared graph shell empty/loading/error patterns.
- [x] Canvas: Fit on graph change; Center on selected; no auto-recenter on every selection change; Reset zoom; card grid keyboard roving + arrows.
- [x] Graph workspace panel responsive grid; canvas selection live region + canvas `aria-label`.
- [x] Graph type legend compact `xs` spacing; benchmark dialogs full-screen on narrow viewports.
