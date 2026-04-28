import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { useI18n } from "../../i18n/useI18n.js";
import { describeTraceabilityState } from "../work/traceabilityState.js";
import GraphCanvasMvp from "./GraphCanvasMvp.jsx";
import { GraphPhysicsPointerBridgeProvider } from "./GraphPhysicsPointerBridgeContext.jsx";
import GraphDebugInspector from "./GraphDebugInspector.jsx";
import GraphFlowView from "./GraphFlowView.jsx";
import GraphSidePanel from "./GraphSidePanel.jsx";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import GraphViewModeSwitch from "./GraphViewModeSwitch.jsx";
import GraphVisualization from "./GraphVisualization.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "./graphShellStates.jsx";
import { firstMatchingNodeIdInOrder } from "./graphNodeSearch.js";
import { LS_GRAPH_STANDALONE_DETAIL_MIN_PX, readGraphDetailColumnPxStored } from "./graphDetailColumnWidth.js";
import WorkspaceGraphToolbar from "./WorkspaceGraphToolbar.jsx";
import { useGraphWorkspaceData } from "./hooks/useGraphWorkspaceData.js";
import { useGraphSelectionReconcile } from "./hooks/useGraphSelectionReconcile.js";
import { useGraphWorkspaceProjection } from "./hooks/useGraphWorkspaceProjection.js";
import { detectCommunitiesForUi } from "./physics/structuralCommunities.js";

const LS_GRAPH_CANVAS_LAYOUT_MODE = "graphCanvasLayoutMode";
const LS_GRAPH_VIZ_MODE = "graphVizMode";
const LS_STANDALONE_DETAILS = "graphStandaloneDetailsVisible";
const LS_STANDALONE_LEGEND = "graphStandaloneLegendOpen";
const LS_EMBEDDED_LEGEND = "graphEmbeddedLegendOpen";
const LS_GRAPH_CANVAS_COLOR_BY = "graphCanvasColorBy";
const LS_GRAPH_CANVAS_COMMUNITY_HULLS = "graphCanvasCommunityHulls";

function readLsMode() {
  if (typeof window === "undefined") return "canvas";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_VIZ_MODE);
    return v === "cards" || v === "canvas" || v === "flow" ? v : "canvas";
  } catch {
    return "canvas";
  }
}

function readLsLayout() {
  if (typeof window === "undefined") return "force";
  try {
    return window.localStorage.getItem(LS_GRAPH_CANVAS_LAYOUT_MODE) === "circle" ? "circle" : "force";
  } catch {
    return "force";
  }
}

function readBoolLs(key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(key);
    if (v == null) return fallback;
    return v === "1";
  } catch {
    return fallback;
  }
}

/** @returns {"type" | "community"} */
function readGraphColorByStored() {
  if (typeof window === "undefined") return "type";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_COLOR_BY);
    if (v === "type" || v === "community") return v;
  } catch {
    /* ignore */
  }
  return "type";
}

export default function GraphWorkspacePanel({
  workId,
  workspaceId = "",
  selectedNodeId = "",
  onSelectNode,
  selectedEdgeId = "",
  onSelectEdge,
  onReconcileSelection,
  mode = "embedded",
  title = "Graph",
  subtitle = null,
  traceContext = {},
  labMode = false,
  focusLayout = false,
  compactLayout = false,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const standalone = mode === "standalone";
  const {
    wsId,
    graph,
    loading,
    error,
    graphVisibility,
    setGraphVisibility,
    wsGraphStats,
    fetchNeighbors,
    expandNeighborsBusy,
    expandAggregatorNode,
    includeInstitutions,
    setIncludeInstitutions,
  } = useGraphWorkspaceData(workspaceId, workId);

  const [vizMode, setVizMode] = useState(() => (standalone ? "canvas" : readLsMode()));
  const [canvasLayoutMode, setCanvasLayoutMode] = useState(() => (standalone ? "force" : readLsLayout()));
  const [detailsVisible, setDetailsVisible] = useState(() => (standalone ? readBoolLs(LS_STANDALONE_DETAILS, !focusLayout) : true));
  const [legendOpen, setLegendOpen] = useState(() =>
    standalone ? readBoolLs(LS_STANDALONE_LEGEND, !focusLayout) : readBoolLs(LS_EMBEDDED_LEGEND, true),
  );
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(labMode);
  const [detailMinPx, setDetailMinPx] = useState(() => readGraphDetailColumnPxStored());
  const [localFindQuery, setLocalFindQuery] = useState("");
  const [centerCanvasNonce, setCenterCanvasNonce] = useState(0);
  const [centerCanvasNodeId, setCenterCanvasNodeId] = useState("");
  const [graphColorBy, setGraphColorBy] = useState(() => readGraphColorByStored());
  const [graphCommunityHulls, setGraphCommunityHulls] = useState(() => readBoolLs(LS_GRAPH_CANVAS_COMMUNITY_HULLS, false));

  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_GRAPH_STANDALONE_DETAIL_MIN_PX, String(detailMinPx));
  }, [standalone, detailMinPx]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_DETAILS, detailsVisible ? "1" : "0");
  }, [standalone, detailsVisible]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_LEGEND, legendOpen ? "1" : "0");
    else window.localStorage.setItem(LS_EMBEDDED_LEGEND, legendOpen ? "1" : "0");
  }, [standalone, legendOpen]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_VIZ_MODE, vizMode);
  }, [standalone, vizMode]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_CANVAS_LAYOUT_MODE, canvasLayoutMode);
  }, [standalone, canvasLayoutMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_COLOR_BY, graphColorBy);
    } catch {
      /* ignore */
    }
  }, [graphColorBy]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_COMMUNITY_HULLS, graphCommunityHulls ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [graphCommunityHulls]);

  const {
    projectedGraph,
    visibleGraph,
    visibilityStats,
    projectedResolvedNodeId,
    resolvedSelectedNodeId,
    resolvedSelectedEdgeId,
    displayGraph,
    capWarnings,
    inspector,
    nodeSearchMatchIds,
  } = useGraphWorkspaceProjection({
    graph,
    graphVisibility,
    selectedNodeId,
    selectedEdgeId,
    localFindQuery,
    t,
  });

  const effectiveVizMode = standalone ? "canvas" : vizMode;
  const effectiveCanvasLayout = standalone ? "force" : canvasLayoutMode;

  const displayGraphNodes = displayGraph?.nodes;
  const displayGraphEdges = displayGraph?.edges;

  const nodeCommunityMap = useMemo(() => {
    const nodes = displayGraphNodes || [];
    const edges = displayGraphEdges || [];
    if (!nodes.length) return new Map();
    const simNodes = nodes.map((n) => ({
      id: n.id,
      type: n.type == null ? "Node" : String(n.type),
      workspaceMembership: n.workspaceMembership == null ? "" : String(n.workspaceMembership).trim().toLowerCase(),
    }));
    const simLinks = edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type == null ? "edge" : String(e.type),
    }));
    return detectCommunitiesForUi(simNodes, simLinks);
  }, [displayGraphNodes, displayGraphEdges]);

  const handleGraphColorByChange = useCallback((v) => {
    setGraphColorBy(v);
    if (v === "type") setGraphCommunityHulls(false);
  }, []);

  useGraphSelectionReconcile({
    selectedNodeId,
    selectedEdgeId,
    resolvedSelectedNodeId,
    resolvedSelectedEdgeId,
    onReconcile: onReconcileSelection,
  });
  const openDetailsOnSelection = useCallback(() => {
    if (!detailsVisible) setDetailsVisible(true);
  }, [detailsVisible]);
  const handleSelectNode = useCallback(
    (id) => {
      if (String(id || "").trim()) openDetailsOnSelection();
      onSelectNode?.(id);
    },
    [onSelectNode, openDetailsOnSelection],
  );
  const handleSelectEdge = useCallback(
    (id) => {
      if (String(id || "").trim()) openDetailsOnSelection();
      onSelectEdge?.(id);
    },
    [onSelectEdge, openDetailsOnSelection],
  );
  const focusFirstLocalMatch = useCallback(() => {
    const first = firstMatchingNodeIdInOrder(displayGraph.nodes, nodeSearchMatchIds);
    if (!first) return;
    openDetailsOnSelection();
    onSelectNode?.(first);
    setCenterCanvasNodeId(first);
    setCenterCanvasNonce((n) => n + 1);
  }, [displayGraph.nodes, nodeSearchMatchIds, onSelectNode, openDetailsOnSelection]);
  const traceSummary = describeTraceabilityState(traceContext);

  const workIdTrim = String(workId || "").trim();
  const hasDataTarget = workIdTrim || String(workspaceId || "").trim();
  const isEmbedded = mode === "embedded";

  return (
    <Box sx={standalone ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" } : {}}>
      <Box sx={{ mb: standalone ? 1 : 2 }}>
        <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
        {subtitle ? <Box sx={{ mt: 0.5 }}>{subtitle}</Box> : null}
      </Box>
      {!hasDataTarget ? <GraphMissingWorkInline message={t("graph.workspacePanel.emptyHint")} /> : null}
      {loading ? <GraphLoadingInline /> : null}
      {error ? <GraphErrorAlert>{error}</GraphErrorAlert> : null}
      {!loading && !error && hasDataTarget ? (
        <>
          <WorkspaceGraphToolbar
            workspaceId={wsId}
            contextWorkId={workIdTrim}
            stats={wsGraphStats}
            visibility={graphVisibility}
            onVisibilityChange={setGraphVisibility}
            canvasMode={effectiveVizMode === "canvas"}
            localFindQuery={localFindQuery}
            onLocalFindChange={(e) => setLocalFindQuery(e.target.value)}
            onLocalFindClear={() => setLocalFindQuery("")}
            onFocusFirstMatch={focusFirstLocalMatch}
            localFindFocusDisabled={nodeSearchMatchIds.size === 0}
            detailsVisible={detailsVisible}
            legendOpen={legendOpen}
            diagnosticsOpen={diagnosticsOpen}
            onToggleDetails={() => setDetailsVisible((v) => !v)}
            onToggleLegend={() => setLegendOpen((v) => !v)}
            onToggleDiagnostics={() => setDiagnosticsOpen((v) => !v)}
            labMode={labMode}
            workGraphIncludeInstitutions={Boolean(includeInstitutions)}
            onToggleWorkGraphIncludeInstitutions={() => setIncludeInstitutions((v) => !v)}
          />
          {!standalone ? <GraphViewModeSwitch mode={vizMode} onChange={setVizMode} compact={compactLayout} /> : null}
          {projectedGraph.warnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Graph data was normalized</Alert> : null}
          {capWarnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Large graph - UI cap is active</Alert> : null}
          <Collapse in={legendOpen}>
            <GraphTypeLegend graph={displayGraph} colorBy={graphColorBy} nodeCommunityMap={nodeCommunityMap} />
          </Collapse>
          <Box
            sx={{
              flex: standalone ? 1 : undefined,
              minHeight: standalone ? 0 : { xs: "auto", md: isEmbedded ? 420 : 520 },
              display: "grid",
              gap: { xs: 2, md: standalone && detailsVisible ? 0 : 2 },
              gridTemplateColumns: !detailsVisible
                ? "minmax(0, 1fr)"
                : { xs: "minmax(0, 1fr)", md: standalone ? `minmax(0, 1fr) 6px ${detailMinPx}px` : "minmax(0, 1.7fr) minmax(280px, 1fr)" },
            }}
          >
            <Box sx={{ minWidth: 0, minHeight: standalone ? 0 : { xs: 280, md: isEmbedded ? 400 : 500 }, display: "flex", flexDirection: "column" }}>
              {effectiveVizMode === "cards" ? (
                <GraphVisualization graph={displayGraph} selectedNodeId={resolvedSelectedNodeId} onSelectNode={handleSelectNode} mode={mode} />
              ) : effectiveVizMode === "flow" ? (
                <GraphFlowView
                  graph={displayGraph}
                  selectedNodeId={resolvedSelectedNodeId}
                  selectedEdgeId={resolvedSelectedEdgeId}
                  onSelectNode={handleSelectNode}
                  onSelectEdge={handleSelectEdge}
                />
              ) : (
                <GraphPhysicsPointerBridgeProvider>
                  <GraphCanvasMvp
                    graph={displayGraph}
                    layoutMode={effectiveCanvasLayout}
                    onCanvasLayoutModeChange={standalone ? undefined : setCanvasLayoutMode}
                    selectedNodeId={resolvedSelectedNodeId}
                    selectedEdgeId={resolvedSelectedEdgeId}
                    onSelectNode={handleSelectNode}
                    onSelectEdge={handleSelectEdge}
                    onAggregatorExpand={(_, expandEndpoint) => expandAggregatorNode(expandEndpoint)}
                    searchQuery={localFindQuery}
                    searchMatchIds={nodeSearchMatchIds}
                    centerRequestNonce={centerCanvasNonce}
                    centerRequestNodeId={centerCanvasNodeId}
                    graphColorBy={graphColorBy}
                    onGraphColorByChange={handleGraphColorByChange}
                    graphCommunityHulls={graphCommunityHulls}
                    onGraphCommunityHullsChange={setGraphCommunityHulls}
                    nodeCommunityMap={nodeCommunityMap}
                  />
                </GraphPhysicsPointerBridgeProvider>
              )}
            </Box>
            <GraphSidePanel
              workspaceId={wsId}
              standalone={standalone}
              visible={detailsVisible}
              selectedNode={inspector.selectedNode}
              selectedEdge={inspector.selectedEdge}
              relatedEdges={inspector.relatedEdges}
              relatedEdgeRows={inspector.relatedEdgeRows}
              authorAuthoredWorks={inspector.authorAuthoredWorks}
              selectedEdgeReadable={inspector.selectedEdgeReadable}
              graphMeta={displayGraph.meta}
              onSelectNode={handleSelectNode}
              onSelectEdge={handleSelectEdge}
              onExpandWorkspaceNeighbors={wsId ? () => fetchNeighbors(resolvedSelectedNodeId) : undefined}
              onAggregatorExpand={(node, expandEndpoint) => {
                handleSelectNode(node?.id || "");
                expandAggregatorNode(expandEndpoint);
              }}
              expandWorkspaceNeighborsBusy={expandNeighborsBusy}
              mode={mode}
              width={detailMinPx}
              onWidthChange={setDetailMinPx}
            />
          </Box>
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 1, columnGap: 1.5, rowGap: 0.5 }}>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
              {t("graph.layerCounts.server", { n: String(graph.nodeCount), e: String(graph.edgeCount) })}
            </Typography>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
              {t("graph.layerCounts.projected", { n: String(projectedGraph.nodeCount), e: String(projectedGraph.edgeCount) })}
            </Typography>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
              {t("graph.layerCounts.visible", { n: String(visibleGraph.nodeCount), e: String(visibleGraph.edgeCount) })}
            </Typography>
            <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted }}>
              {t("graph.layerCounts.display", { n: String(displayGraph.nodeCount), e: String(displayGraph.edgeCount) })}
            </Typography>
          </Box>
          {traceSummary.length > 0 ? <Alert severity="info" sx={{ mt: 1 }}>Opened from traceability context: {traceSummary.join(" · ")}</Alert> : null}
          {projectedGraph.nodeCount === 0 ? <Alert severity="info" sx={{ mt: 1 }}>This response has no nodes yet.</Alert> : null}
          <Box sx={{ mt: 1 }}>
            <GraphDebugInspector
              visible={labMode || diagnosticsOpen}
              maxHeight={standalone ? 200 : isEmbedded ? 180 : 240}
              payload={{
                work_id: projectedGraph.workId,
                meta: projectedGraph.meta,
                selected_node_id: resolvedSelectedNodeId,
                selected_node_id_projected: projectedResolvedNodeId,
                selected_edge_id: resolvedSelectedEdgeId,
                counts: {
                  normalized_server: { nodes: graph.nodeCount, edges: graph.edgeCount },
                  projected: { nodes: projectedGraph.nodeCount, edges: projectedGraph.edgeCount },
                  visible_after_nodes_filter: { nodes: visibleGraph.nodeCount, edges: visibleGraph.edgeCount },
                  display_after_ui_cap: { nodes: displayGraph.nodeCount, edges: displayGraph.edgeCount },
                },
                visibility_filter: {
                  types: graphVisibility.types,
                  show_external_works: graphVisibility.showExternalWorks,
                  show_claims: Array.isArray(graphVisibility.types) && graphVisibility.types.includes("Claim"),
                  hidden_nodes_by_type: visibilityStats.hiddenNodesByType,
                  hidden_nodes_as_external: visibilityStats.hiddenNodesAsExternal,
                  hidden_nodes_as_claims_extension: visibilityStats.hiddenNodesAsClaims,
                  hidden_edges_due_to_nodes: visibilityStats.hiddenEdges,
                },
                hidden_nodes_ui_cap_estimate: Math.max(0, visibleGraph.nodeCount - displayGraph.nodeCount),
                hidden_edges_ui_cap_estimate: Math.max(0, visibleGraph.edgeCount - displayGraph.edgeCount),
                warnings: projectedGraph.warnings,
                ui_cap_warnings: capWarnings,
              }}
            />
          </Box>
        </>
      ) : null}
    </Box>
  );
}
