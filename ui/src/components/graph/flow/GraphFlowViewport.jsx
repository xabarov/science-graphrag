import React, { useCallback } from "react";
import Box from "@mui/material/Box";
import { Background, Controls, MiniMap, ReactFlow } from "@xyflow/react";

import { useTheme } from "@mui/material/styles";

import { getScienceGraphNodeStyle } from "../canvas/graphCanvasStyle.js";
import { GRAPH_FLOW_MIN_VIEW_HEIGHT } from "./graphFlowConstants.js";

/**
 * @param {{
 *   nodes: import("@xyflow/react").Node[],
 *   edges: import("@xyflow/react").Edge[],
 *   onNodesChange: import("@xyflow/react").OnNodesChange,
 *   onEdgesChange: import("@xyflow/react").OnEdgesChange,
 *   nodeTypes: Record<string, import("react").ComponentType>,
 *   onNodeClick: import("@xyflow/react").NodeMouseHandler,
 *   onEdgeClick: import("@xyflow/react").EdgeMouseHandler,
 *   onPaneClick: () => void,
 *   showMinimap: boolean,
 * }} props
 */
export default function GraphFlowViewport({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  nodeTypes,
  onNodeClick,
  onEdgeClick,
  onPaneClick,
  showMinimap,
}) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const appearance = theme.palette.mode === "light" ? "light" : "dark";

  const minimapNodeColor = useCallback(
    (node) => {
      const st = getScienceGraphNodeStyle(node?.data?.nodeType, { appearance });
      return st.fill || tk.border.default;
    },
    [appearance, tk.border.default],
  );

  return (
    <Box sx={{ flex: 1, minHeight: GRAPH_FLOW_MIN_VIEW_HEIGHT, minWidth: 0, position: "relative" }}>
      <Box sx={{ position: "absolute", inset: 0 }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          fitView
          minZoom={0.04}
          maxZoom={4}
          nodesConnectable={false}
          nodesDraggable={false}
          onlyRenderVisibleElements
          elevateEdgesOnSelect
          elevateNodesOnSelect
          style={{ width: "100%", height: "100%" }}
          proOptions={{ hideAttribution: true }}
          aria-label="Interactive graph: pan and zoom; click a node or edge to select it."
        >
          <Background color={tk.border.default} gap={20} />
          <Controls showInteractive={false} />
          {showMinimap ? (
            <MiniMap
              position="bottom-right"
              pannable
              zoomable
              nodeStrokeWidth={2}
              nodeColor={minimapNodeColor}
              maskColor={appearance === "light" ? "rgba(248,250,252,0.72)" : "rgba(10, 10, 10, 0.72)"}
              style={{
                backgroundColor: tk.surface.sidebar,
                border: `1px solid ${tk.border.strong}`,
                borderRadius: 6,
              }}
            />
          ) : null}
        </ReactFlow>
      </Box>
    </Box>
  );
}
