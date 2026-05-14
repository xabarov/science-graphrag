import React, { useCallback } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useReactFlow } from "@xyflow/react";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";
import { localizeEdgeType } from "../model/graphLocalize.js";
import { GRAPH_FLOW_NODE_TYPES } from "./graphFlowNodeTypes.js";
import GraphFlowToolbar from "./GraphFlowToolbar.jsx";
import GraphFlowViewport from "./GraphFlowViewport.jsx";
import { useGraphFlowSelectionHandlers } from "./hooks/useGraphFlowSelectionHandlers.js";
import { useGraphFlowState } from "./hooks/useGraphFlowState.js";

/**
 * @param {{
 *   graph: { nodes: Array<{ id: string }>, edges: Array<{ id: string, source: string, target: string }> },
 *   selectedNodeId: string,
 *   selectedEdgeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 * }} props
 */
export default function GraphFlowInner({ graph, selectedNodeId, selectedEdgeId = "", onSelectNode, onSelectEdge }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const resolveEdgeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const { fitView, zoomTo } = useReactFlow();

  const { nodes, edges, onNodesChange, onEdgesChange, showMinimap, setShowMinimap } = useGraphFlowState({
    graph,
    selectedNodeId,
    selectedEdgeId,
    resolveEdgeLabel,
    fitView,
  });

  const {
    handleFitAll,
    handleResetZoom,
    handleCenterSelection,
    onNodeClick,
    onEdgeClick,
    onPaneClick,
    handleKeyDown,
    liveRegionText,
    canCenter,
  } = useGraphFlowSelectionHandlers({
    graph,
    selectedNodeId,
    selectedEdgeId,
    onSelectNode,
    onSelectEdge,
    fitView,
    zoomTo,
  });

  return (
    <Box
      component="section"
      role="region"
      aria-label="Graph flow"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      sx={{
        width: "100%",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        overflow: "hidden",
        backgroundColor: tk.surface.panel,
        position: "relative",
        outline: "none",
        alignSelf: "stretch",
        "&:focus-visible": {
          boxShadow: `0 0 0 1px ${tk.accent.softBorder}`,
        },
      }}
    >
      <Typography
        component="div"
        aria-live="polite"
        sx={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {liveRegionText}
      </Typography>
      <GraphFlowToolbar
        tk={tk}
        handleFitAll={handleFitAll}
        handleResetZoom={handleResetZoom}
        handleCenterSelection={handleCenterSelection}
        canCenter={canCenter}
        showMinimap={showMinimap}
        setShowMinimap={setShowMinimap}
      />
      <GraphFlowViewport
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={GRAPH_FLOW_NODE_TYPES}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        showMinimap={showMinimap}
      />
    </Box>
  );
}
