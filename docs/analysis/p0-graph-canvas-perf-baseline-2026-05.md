# P0 graph canvas — perf baseline and mitigation knobs (2026-05)

Companion to [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) P0 «canvas perf for very large payloads».

## Measurement

1. **Telemetry:** set `localStorage science-graphrag:graphTelemetry=1` — logs payload sizes (`graph.workspace.payload`) from [`useGraphWorkspaceProjection`](../../ui/src/components/graph/workspace/hooks/useGraphWorkspaceProjection.js).

2. **Performance marks:** set `localStorage science-graphrag:graphPerf=1` — measures stages `graph.projectAuthorSemantic`, `graph.visibilityFilter`, `graph.capForUi`, `graph.inspectorDetail` via [`graphPerfInstrumentation.js`](../../ui/src/components/graph/model/graphPerfInstrumentation.js). Inspect Chrome **Performance** → User timings. (Implementation clears mark names after each `measure` to keep the mark list small during long recordings.)

3. **Manual:** record Long Tasks and time-to-first-interaction on a dense workspace snapshot (DevTools Performance).

## Reference thresholds (client)

| Constant | Location | Purpose |
|----------|----------|---------|
| `WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT` (5000) | [`graphUiLimits.js`](../../ui/src/components/graph/model/graphUiLimits.js) | Non-blocking warning; full graph still rendered |
| `WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT` (10000) | same | same |
| `COMMUNITY_DETECTION_MAX_NODES` (6000) | [`simConstants.js`](../../ui/src/components/graph/canvas/physics/simConstants.js) | Skip hybrid community detection in force sim + cheap legend map |
| `COMMUNITY_DETECTION_MAX_LINKS` (14000) | same | same |
| `EDGE_LABEL_MEGA_DENSE_MIN_EDGES` (4000) | [`graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js) | Adaptive edge mid-labels behave like interaction-only |

Fill the table below when profiling a real workspace (N nodes / E edges):

| N | E | Worst long task (ms) | Notes |
|---|---|----------------------|-------|
|   |   |                      |       |

## Product note

Display truncation and server-side subsets are **out of scope** for this doc unless explicitly approved; current UX uses warnings + cheaper rendering paths only.
