import React from "react";
import Box from "@mui/material/Box";

import GraphCanvasMvp from "../../canvas/GraphCanvasMvp.jsx";
import { GraphPhysicsPointerBridgeProvider } from "../../canvas/GraphPhysicsPointerBridgeContext.jsx";
import GraphFlowView from "../../flow/GraphFlowView.jsx";
import GraphSidePanel from "../../shell/GraphSidePanel.jsx";
import GraphVisualization from "../../shell/GraphVisualization.jsx";

/**
 * Main grid: visualization (cards / flow / canvas) + side detail panel.
 *
 * @param {{
 *   standalone: boolean,
 *   isEmbedded: boolean,
 *   detailsVisible: boolean,
 *   detailMinPx: number,
 *   effectiveVizMode: string,
 *   effectiveCanvasLayout: string,
 *   displayGraph: object,
 *   resolvedSelectedNodeId: string,
 *   resolvedSelectedEdgeId: string,
 *   handleSelectNode: (id: string) => void,
 *   handleSelectEdge: (id: string) => void,
 *   setCanvasLayoutMode: (v: string) => void,
 *   expandAggregatorNode: (endpoint: string) => void | Promise<void>,
 *   localFindQuery: string,
 *   nodeSearchMatchIds: Set<string>,
 *   centerCanvasNonce: number,
 *   centerCanvasNodeId: string,
 *   graphColorBy: string,
 *   handleGraphColorByChange: (v: string) => void,
 *   graphCommunityHulls: boolean,
 *   setGraphCommunityHulls: React.Dispatch<React.SetStateAction<boolean>>,
 *   nodeCommunityMap: Map<string, unknown>,
 *   wsId: string,
 *   inspector: object,
 *   mode: string,
 *   setDetailMinPx: React.Dispatch<React.SetStateAction<number>>,
 *   fetchNeighbors: (nodeId: string) => void | Promise<void>,
 *   expandNeighborsBusy: boolean,
 * }} props
 */
export default function GraphWorkspaceMainSection({
  standalone,
  isEmbedded,
  detailsVisible,
  detailMinPx,
  effectiveVizMode,
  effectiveCanvasLayout,
  displayGraph,
  resolvedSelectedNodeId,
  resolvedSelectedEdgeId,
  handleSelectNode,
  handleSelectEdge,
  setCanvasLayoutMode,
  expandAggregatorNode,
  localFindQuery,
  nodeSearchMatchIds,
  centerCanvasNonce,
  centerCanvasNodeId,
  graphColorBy,
  handleGraphColorByChange,
  graphCommunityHulls,
  setGraphCommunityHulls,
  nodeCommunityMap,
  wsId,
  inspector,
  mode,
  setDetailMinPx,
  fetchNeighbors,
  expandNeighborsBusy,
}) {
  return (
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
  );
}
