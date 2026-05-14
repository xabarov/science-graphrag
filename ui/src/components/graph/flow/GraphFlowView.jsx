import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { ReactFlowProvider } from "@xyflow/react";
import { useTheme } from "@mui/material/styles";

import { GRAPH_FLOW_MIN_VIEW_HEIGHT } from "./graphFlowConstants.js";
import GraphFlowInner from "./GraphFlowInner.jsx";

import "@xyflow/react/dist/style.css";

/**
 * Phase B: React Flow view with Canvas-like navigation (fit, reset zoom, center, Escape).
 *
 * @param {{
 *   graph: { nodes: Array<{ id: string }>, edges: Array<{ id: string, source: string, target: string }> },
 *   selectedNodeId: string,
 *   selectedEdgeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 * }} props
 */
export default function GraphFlowView({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
}) {
  const tk = useTheme().appTokens;
  const nodeCount = Array.isArray(graph?.nodes) ? graph.nodes.length : 0;
  if (nodeCount === 0) {
    return (
      <Box
        component="section"
        role="region"
        aria-label="Graph flow"
        sx={{
          borderRadius: "6px",
          border: `1px solid ${tk.border.default}`,
          backgroundColor: tk.surface.panel,
          minHeight: GRAPH_FLOW_MIN_VIEW_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>No nodes to show in Flow view.</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: GRAPH_FLOW_MIN_VIEW_HEIGHT,
        minWidth: 0,
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <ReactFlowProvider>
        <GraphFlowInner
          graph={graph}
          selectedNodeId={selectedNodeId}
          selectedEdgeId={selectedEdgeId}
          onSelectNode={onSelectNode}
          onSelectEdge={onSelectEdge}
        />
      </ReactFlowProvider>
    </Box>
  );
}
