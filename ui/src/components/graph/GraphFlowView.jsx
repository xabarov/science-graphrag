import React, { memo, useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";

import "@xyflow/react/dist/style.css";

import { CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { getScienceGraphNodeStyle } from "./graphCanvasStyle.js";
import { buildReactFlowEdges, buildReactFlowNodes, getGraphLayoutSignature } from "./graphFlowAdapter.js";
import { localizeEdgeType } from "./graphLocalize.js";

const MIN_VIEW_HEIGHT = 280;
const LS_GRAPH_FLOW_MINIMAP = "graphFlowMinimap";

function readMinimapPreference() {
  if (typeof window === "undefined") return true;
  try {
    const v = window.localStorage.getItem(LS_GRAPH_FLOW_MINIMAP);
    if (v === null) return true;
    return v === "1";
  } catch {
    return true;
  }
}

/**
 * @param {import("@xyflow/react").Node} node
 * @returns {string}
 */
function minimapNodeColor(node) {
  const st = getScienceGraphNodeStyle(node?.data?.nodeType, {});
  return st.fill || "rgba(255,255,255,0.12)";
}

/**
 * Custom node: type-colored chip (parity with {@link GraphCanvasMvp}).
 * @param {import("@xyflow/react").NodeProps<{ label: string, nodeType?: string }>} props
 */
const ScienceGraphNode = memo(function ScienceGraphNode({ data, selected }) {
  const st = getScienceGraphNodeStyle(data.nodeType, { selected });
  return (
    <div
      style={{
        padding: "6px 10px",
        borderRadius: 8,
        border: `${st.lineWidth}px solid ${st.stroke}`,
        backgroundColor: st.fill,
        color: "rgba(255,255,255,0.88)",
        fontSize: 11,
        fontWeight: 600,
        minWidth: 40,
        maxWidth: 160,
        textAlign: "center",
        lineHeight: 1.25,
      }}
    >
      <Handle type="target" position={Position.Top} id="in" style={{ opacity: 0.35, width: 7, height: 7 }} />
      {data.label}
      <Handle type="source" position={Position.Bottom} id="out" style={{ opacity: 0.35, width: 7, height: 7 }} />
    </div>
  );
});

const NODE_TYPES = { science: ScienceGraphNode };

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
function GraphFlowInner({ graph, selectedNodeId, selectedEdgeId = "", onSelectNode, onSelectEdge }) {
  const { t } = useI18n();
  const resolveEdgeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const { fitView, zoomTo } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showMinimap, setShowMinimap] = useState(readMinimapPreference);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_FLOW_MINIMAP, showMinimap ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [showMinimap]);

  const layoutSignature = useMemo(() => getGraphLayoutSignature(graph), [graph]);

  const nextNodes = useMemo(
    () => buildReactFlowNodes(graph, selectedNodeId),
    [graph, selectedNodeId],
  );
  const nextEdges = useMemo(
    () => buildReactFlowEdges(graph, selectedEdgeId, { resolveEdgeLabel }),
    [graph, resolveEdgeLabel, selectedEdgeId],
  );

  useEffect(() => {
    setNodes(nextNodes);
    setEdges(nextEdges);
  }, [nextEdges, nextNodes, setEdges, setNodes]);

  useEffect(() => {
    const id = window.requestAnimationFrame(() => {
      void fitView({ padding: 0.2, duration: 200 });
    });
    return () => window.cancelAnimationFrame(id);
  }, [layoutSignature, fitView]);

  const handleFitAll = useCallback(() => {
    void fitView({ padding: 0.2, duration: 200 });
  }, [fitView]);

  const handleResetZoom = useCallback(() => {
    void zoomTo(1, { duration: 150 });
  }, [zoomTo]);

  const handleCenterSelection = useCallback(() => {
    const nodeId = String(selectedNodeId || "").trim();
    const edgeId = String(selectedEdgeId || "").trim();
    if (nodeId) {
      void fitView({
        nodes: [{ id: nodeId }],
        padding: 0.35,
        duration: 250,
        maxZoom: 2,
      });
      return;
    }
    if (edgeId) {
      const e = graph.edges.find((ed) => ed.id === edgeId);
      if (e) {
        void fitView({
          nodes: [{ id: e.source }, { id: e.target }],
          padding: 0.4,
          duration: 250,
        });
      }
    }
  }, [fitView, graph.edges, selectedEdgeId, selectedNodeId]);

  const onNodeClick = useCallback(
    (_evt, node) => {
      onSelectEdge?.("");
      onSelectNode?.(node.id);
    },
    [onSelectEdge, onSelectNode],
  );

  const onEdgeClick = useCallback(
    (_evt, edge) => {
      onSelectNode?.("");
      onSelectEdge?.(edge.id);
    },
    [onSelectEdge, onSelectNode],
  );

  const onPaneClick = useCallback(() => {
    onSelectNode?.("");
    onSelectEdge?.("");
  }, [onSelectEdge, onSelectNode]);

  const handleKeyDown = useCallback(
    (ev) => {
      if (ev.key === "Escape") {
        ev.preventDefault();
        onSelectNode?.("");
        onSelectEdge?.("");
      }
    },
    [onSelectEdge, onSelectNode],
  );

  const live =
    selectedEdgeId && String(selectedEdgeId).trim()
      ? `Edge ${String(selectedEdgeId).trim()} selected.`
      : selectedNodeId && String(selectedNodeId).trim()
        ? `Node ${String(selectedNodeId).trim()} selected.`
        : "No node or edge selected.";

  const canCenter = Boolean(String(selectedNodeId || "").trim() || String(selectedEdgeId || "").trim());

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
        border: "1px solid rgba(255,255,255,0.08)",
        overflow: "hidden",
        backgroundColor: "#0a0a0a",
        position: "relative",
        outline: "none",
        alignSelf: "stretch",
        "&:focus-visible": {
          boxShadow: "0 0 0 1px rgba(99, 102, 241, 0.5)",
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
        {live}
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, px: 1.5, pt: 1, pb: 0.5, flexShrink: 0 }}>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", flex: "1 1 140px" }}>
          Wheel zooms · drag to pan · click node or edge · Escape clears selection (focus panel first). Same URL selection as
          Canvas.
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          <CursorSmallButton type="button" onClick={handleFitAll}>
            Fit
          </CursorSmallButton>
          <CursorSmallButton type="button" onClick={handleResetZoom}>
            Reset zoom
          </CursorSmallButton>
          <CursorSmallButton type="button" onClick={handleCenterSelection} disabled={!canCenter}>
            Center on selected
          </CursorSmallButton>
          <CursorSmallButton
            type="button"
            onClick={() => setShowMinimap((v) => !v)}
            aria-pressed={showMinimap}
          >
            {showMinimap ? "Hide" : "Show"} minimap
          </CursorSmallButton>
        </Box>
      </Box>
      <Box sx={{ flex: 1, minHeight: MIN_VIEW_HEIGHT, minWidth: 0, position: "relative" }}>
        <Box sx={{ position: "absolute", inset: 0 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={NODE_TYPES}
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
            <Background color="rgba(255,255,255,0.06)" gap={20} />
            <Controls showInteractive={false} />
            {showMinimap ? (
              <MiniMap
                position="bottom-right"
                pannable
                zoomable
                nodeStrokeWidth={2}
                nodeColor={minimapNodeColor}
                maskColor="rgba(10, 10, 10, 0.72)"
                style={{
                  backgroundColor: "#141414",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 6,
                }}
              />
            ) : null}
          </ReactFlow>
        </Box>
      </Box>
    </Box>
  );
}

export default function GraphFlowView({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
}) {
  const nodeCount = Array.isArray(graph?.nodes) ? graph.nodes.length : 0;
  if (nodeCount === 0) {
    return (
      <Box
        component="section"
        role="region"
        aria-label="Graph flow"
        sx={{
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          minHeight: MIN_VIEW_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No nodes to show in Flow view.</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        flex: 1,
        minHeight: MIN_VIEW_HEIGHT,
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
