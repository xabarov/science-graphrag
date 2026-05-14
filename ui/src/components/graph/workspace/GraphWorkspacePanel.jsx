import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { useI18n } from "../../../i18n/useI18n.js";
import { describeTraceabilityState } from "../../work/traceability/traceabilityState.js";
import GraphTypeLegend from "../shell/GraphTypeLegend.jsx";
import GraphViewModeSwitch from "../shell/GraphViewModeSwitch.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "../shell/graphShellStates.jsx";
import GraphWorkspaceOnboarding from "./GraphWorkspaceOnboarding.jsx";
import WorkspaceGraphToolbar from "./WorkspaceGraphToolbar.jsx";
import GraphWorkspaceLayerCountsFooter from "./GraphWorkspaceLayerCountsFooter.jsx";
import { useGraphWorkspaceData } from "./hooks/useGraphWorkspaceData.js";
import { useGraphSelectionReconcile } from "../hooks/useGraphSelectionReconcile.js";
import { useGraphWorkspaceProjection } from "./hooks/useGraphWorkspaceProjection.js";
import { useGraphWorkspacePanelActions } from "./hooks/useGraphWorkspacePanelActions.js";
import { useGraphWorkspacePanelCommunityMap } from "./hooks/useGraphWorkspacePanelCommunityMap.js";
import { useGraphWorkspacePanelState } from "./hooks/useGraphWorkspacePanelState.js";
import GraphWorkspaceAlertsAboveMainGrid from "./sections/GraphWorkspaceAlertsAboveMainGrid.jsx";
import GraphWorkspaceAlertsBelowFooter from "./sections/GraphWorkspaceAlertsBelowFooter.jsx";
import GraphWorkspaceDebugInspectorSection from "./sections/GraphWorkspaceDebugInspectorSection.jsx";
import GraphWorkspaceMainSection from "./sections/GraphWorkspaceMainSection.jsx";

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
  standaloneToolbarLeading = null,
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

  const {
    vizMode,
    setVizMode,
    canvasLayoutMode,
    setCanvasLayoutMode,
    detailsVisible,
    setDetailsVisible,
    legendOpen,
    setLegendOpen,
    diagnosticsOpen,
    setDiagnosticsOpen,
    detailMinPx,
    setDetailMinPx,
    localFindQuery,
    setLocalFindQuery,
    centerCanvasNonce,
    setCenterCanvasNonce,
    centerCanvasNodeId,
    setCenterCanvasNodeId,
    graphColorBy,
    setGraphColorBy,
    graphCommunityHulls,
    setGraphCommunityHulls,
  } = useGraphWorkspacePanelState({ standalone, focusLayout, labMode });

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

  const nodeCommunityMap = useGraphWorkspacePanelCommunityMap({ displayGraph });

  const { handleGraphColorByChange, handleSelectNode, handleSelectEdge, focusFirstLocalMatch } = useGraphWorkspacePanelActions({
    detailsVisible,
    setDetailsVisible,
    onSelectNode,
    onSelectEdge,
    displayGraph,
    nodeSearchMatchIds,
    setGraphColorBy,
    setGraphCommunityHulls,
    setCenterCanvasNodeId,
    setCenterCanvasNonce,
  });

  useGraphSelectionReconcile({
    selectedNodeId,
    selectedEdgeId,
    resolvedSelectedNodeId,
    resolvedSelectedEdgeId,
    onReconcile: onReconcileSelection,
  });

  const traceSummary = describeTraceabilityState(traceContext);

  const workIdTrim = String(workId || "").trim();
  const hasDataTarget = workIdTrim || String(workspaceId || "").trim();
  const isEmbedded = mode === "embedded";

  const debugPayload = useMemo(
    () => ({
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
    }),
    [
      capWarnings,
      displayGraph,
      graph.edgeCount,
      graph.nodeCount,
      graphVisibility,
      projectedGraph.edgeCount,
      projectedGraph.meta,
      projectedGraph.nodeCount,
      projectedGraph.warnings,
      projectedGraph.workId,
      projectedResolvedNodeId,
      resolvedSelectedEdgeId,
      resolvedSelectedNodeId,
      visibilityStats.hiddenEdges,
      visibilityStats.hiddenNodesAsClaims,
      visibilityStats.hiddenNodesAsExternal,
      visibilityStats.hiddenNodesByType,
      visibleGraph.edgeCount,
      visibleGraph.nodeCount,
    ],
  );

  return (
    <Box sx={standalone ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" } : {}}>
      {title || subtitle ? (
        <Box sx={{ mb: standalone ? 1 : 2 }}>
          {title ? <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{title}</Typography> : null}
          {subtitle ? <Box sx={{ mt: 0.5 }}>{subtitle}</Box> : null}
        </Box>
      ) : null}
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
            dense={Boolean(compactLayout || focusLayout)}
            leadingSlot={standalone && standaloneToolbarLeading ? standaloneToolbarLeading : null}
          />
          {standalone && effectiveVizMode === "canvas" ? <GraphWorkspaceOnboarding t={t} /> : null}
          {!standalone ? <GraphViewModeSwitch mode={vizMode} onChange={setVizMode} compact={compactLayout} /> : null}
          <GraphWorkspaceAlertsAboveMainGrid
            projectedGraph={projectedGraph}
            capWarnings={capWarnings}
            displayGraphNodes={displayGraphNodes}
            displayGraphEdges={displayGraphEdges}
            t={t}
          />
          <Collapse in={legendOpen}>
            <GraphTypeLegend graph={displayGraph} colorBy={graphColorBy} nodeCommunityMap={nodeCommunityMap} />
          </Collapse>
          <GraphWorkspaceMainSection
            standalone={standalone}
            isEmbedded={isEmbedded}
            detailsVisible={detailsVisible}
            detailMinPx={detailMinPx}
            effectiveVizMode={effectiveVizMode}
            effectiveCanvasLayout={effectiveCanvasLayout}
            displayGraph={displayGraph}
            resolvedSelectedNodeId={resolvedSelectedNodeId}
            resolvedSelectedEdgeId={resolvedSelectedEdgeId}
            handleSelectNode={handleSelectNode}
            handleSelectEdge={handleSelectEdge}
            setCanvasLayoutMode={setCanvasLayoutMode}
            expandAggregatorNode={expandAggregatorNode}
            localFindQuery={localFindQuery}
            nodeSearchMatchIds={nodeSearchMatchIds}
            centerCanvasNonce={centerCanvasNonce}
            centerCanvasNodeId={centerCanvasNodeId}
            graphColorBy={graphColorBy}
            handleGraphColorByChange={handleGraphColorByChange}
            graphCommunityHulls={graphCommunityHulls}
            setGraphCommunityHulls={setGraphCommunityHulls}
            nodeCommunityMap={nodeCommunityMap}
            wsId={wsId}
            inspector={inspector}
            mode={mode}
            setDetailMinPx={setDetailMinPx}
            fetchNeighbors={fetchNeighbors}
            expandNeighborsBusy={expandNeighborsBusy}
          />
          <GraphWorkspaceLayerCountsFooter
            t={t}
            tk={tk}
            graph={graph}
            projectedGraph={projectedGraph}
            visibleGraph={visibleGraph}
            displayGraph={displayGraph}
          />
          <GraphWorkspaceAlertsBelowFooter traceSummary={traceSummary} projectedGraph={projectedGraph} t={t} />
          <GraphWorkspaceDebugInspectorSection
            visible={labMode || diagnosticsOpen}
            maxHeight={standalone ? 200 : isEmbedded ? 180 : 240}
            payload={debugPayload}
          />
        </>
      ) : null}
    </Box>
  );
}
