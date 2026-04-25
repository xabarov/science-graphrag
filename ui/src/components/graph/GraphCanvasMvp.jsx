import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Slider from "@mui/material/Slider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CenterFocusStrongOutlinedIcon from "@mui/icons-material/CenterFocusStrongOutlined";
import FitScreenOutlinedIcon from "@mui/icons-material/FitScreenOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LinkOffOutlinedIcon from "@mui/icons-material/LinkOffOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import ZoomOutMapOutlinedIcon from "@mui/icons-material/ZoomOutMapOutlined";

import { CursorIconButton } from "../common/index.js";
import { computeFitTransform, computeWorldLayout, screenToWorld, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { drawEdges, drawLabels, drawNodes } from "./graphCanvasDraw.js";
import { getGraphLayoutSignature } from "./graphFlowAdapter.js";
import { buildSimulationState } from "./graphSimulationAdapter.js";
import useGraphCanvasInput from "./hooks/useGraphCanvasInput.js";
import { useScienceGraphForceSimulation } from "./physics/useScienceGraphForceSimulation.js";
import { percentToRepulsion, REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";

const NODE_RADIUS = 12;
const FIT_PADDING = 40;
const MIN_CANVAS_HEIGHT = 280;
const MIN_FIT_SCALE = 0.11;
const FORCE_RESTART_JITTER_WORLD = 56;
const LS_GRAPH_CANVAS_REPULSION = "graphCanvasRepulsionPercent";
const MIN_SCALE = 0.06;
const MAX_SCALE = 8;

function clampFitTransform(fit) {
  return { ...fit, scale: Math.max(fit.scale, MIN_FIT_SCALE) };
}

function readRepulsionPercentStored() {
  if (typeof window === "undefined") return REPULSION_DEFAULT_PERCENT;
  try {
    const raw = window.localStorage.getItem(LS_GRAPH_CANVAS_REPULSION);
    const n = Number(raw);
    if (!Number.isFinite(n)) return REPULSION_DEFAULT_PERCENT;
    return Math.min(100, Math.max(0, n));
  } catch {
    return REPULSION_DEFAULT_PERCENT;
  }
}

export default function GraphCanvasMvp({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
  layoutMode = "circle",
  onCanvasLayoutModeChange,
  onAggregatorExpand,
}) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const canvasHostRef = useRef(null);
  const positionsRef = useRef(new Map());
  const transformRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const fixedNodesRef = useRef(new Set());
  const draggedNodePositionRef = useRef(null);
  const simNodesRef = useRef([]);
  const prevLayoutModeRef = useRef(layoutMode);

  const [transform, setTransform] = useState({ scale: 1, tx: 0, ty: 0 });
  const [hostSize, setHostSize] = useState({ width: 0, height: 0 });
  const [simNodes, setSimNodes] = useState([]);
  const [simLinks, setSimLinks] = useState([]);
  const [isSimulationStable, setIsSimulationStable] = useState(false);
  const [repulsionPercent, setRepulsionPercent] = useState(() => readRepulsionPercentStored());
  const [forceSimRunNonce, setForceSimRunNonce] = useState(0);
  const [physicsReheatNonce, setPhysicsReheatNonce] = useState(0);
  const [pinnedNodeCount, setPinnedNodeCount] = useState(0);

  const topologySignature = useMemo(() => getGraphLayoutSignature({ nodes: graph.nodes, edges: graph.edges }), [graph.nodes, graph.edges]);
  const simulationSignature = useMemo(
    () => `${topologySignature}|${forceSimRunNonce}|${physicsReheatNonce}`,
    [topologySignature, forceSimRunNonce, physicsReheatNonce],
  );
  const repulsionStrength = useMemo(() => percentToRepulsion(repulsionPercent), [repulsionPercent]);
  const layoutWorldRadius = useMemo(() => worldRadiusForNodeCount(graph.nodes.length), [graph.nodes.length]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const canvasSize = useMemo(
    () => ({ width: Math.max(1, hostSize.width || 1), height: Math.max(MIN_CANVAS_HEIGHT, hostSize.height || MIN_CANVAS_HEIGHT) }),
    [hostSize.height, hostSize.width],
  );
  useEffect(() => {
    simNodesRef.current = simNodes;
  }, [simNodes]);

  const getViewportDims = useCallback(() => {
    const host = canvasHostRef.current;
    return {
      w: Math.max(1, hostSize.width || host?.clientWidth || 1),
      h: Math.max(MIN_CANVAS_HEIGHT, hostSize.height || host?.clientHeight || MIN_CANVAS_HEIGHT),
    };
  }, [hostSize.height, hostSize.width]);

  const getPositionsForFrame = useCallback(() => {
    if (simNodes.length > 0 && layoutMode === "force") return new Map(simNodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    return computeWorldLayout(graph.nodes, layoutWorldRadius);
  }, [graph.nodes, layoutMode, layoutWorldRadius, simNodes]);

  const applyFit = useCallback(
    (mode = "auto") => {
      if (graph.nodes.length === 0) return;
      const { w, h } = getViewportDims();
      const useForce = (mode === "force" || (mode === "auto" && layoutMode === "force")) && simNodesRef.current.length > 0;
      const positions = useForce
        ? new Map(simNodesRef.current.map((n) => [n.id, { x: n.x, y: n.y }]))
        : computeWorldLayout(graph.nodes, layoutWorldRadius);
      positionsRef.current = positions;
      const next = clampFitTransform(computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING));
      transformRef.current = next;
      setTransform(next);
    },
    [getViewportDims, graph.nodes, layoutMode, layoutWorldRadius],
  );

  const onNodeClick = useCallback(
    (nodeId) => {
      const clickedNode = nodeById.get(nodeId);
      if (clickedNode?.nodeKind === "Aggregator") {
        const expandUrl = clickedNode.raw?.aggregation_hints?.expand_endpoint;
        if (expandUrl) onAggregatorExpand?.(clickedNode, expandUrl);
        return;
      }
      onSelectEdge?.("");
      onSelectNode?.(nodeId);
    },
    [nodeById, onAggregatorExpand, onSelectEdge, onSelectNode],
  );

  const input = useGraphCanvasInput({
    canvasRef,
    graph,
    nodeById,
    transformRef,
    setTransform,
    onNodeClick,
    onEdgeClick: (edgeId) => {
      onSelectNode?.("");
      onSelectEdge?.(edgeId);
    },
    onCanvasClick: () => {
      onSelectNode?.("");
      onSelectEdge?.("");
    },
    getPositionsForFrame,
    layoutMode,
    onCanvasLayoutModeChange,
    simNodes,
    setSimNodes,
    isSimulationStable,
    setIsSimulationStable,
    bumpPhysicsReheat: () => setPhysicsReheatNonce((n) => n + 1),
    draggedNodePositionRef,
    fixedNodesRef,
    setPinnedNodeCount,
  });

  useScienceGraphForceSimulation(
    layoutMode === "force" && simNodes.length > 0,
    simNodes,
    setSimNodes,
    simLinks,
    repulsionStrength,
    isSimulationStable,
    setIsSimulationStable,
    fixedNodesRef,
    draggedNodePositionRef,
    canvasSize,
    simulationSignature,
  );

  useLayoutEffect(() => {
    const built = buildSimulationState(graph);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- topology re-seed is intentional
    setSimNodes(built.nodes);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- topology re-seed is intentional
    setSimLinks(built.links);
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
    setForceSimRunNonce(0);
    setPhysicsReheatNonce(0);
    positionsRef.current = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    if (layoutMode === "force" && built.nodes.length > 0) applyFit("force");
    // eslint-disable-next-line react-hooks/exhaustive-deps -- re-seed on topologySignature only; omit graph so selection/new object identity does not reset sim
  }, [topologySignature, layoutMode, applyFit]);

  useEffect(() => {
    const prev = prevLayoutModeRef.current;
    prevLayoutModeRef.current = layoutMode;
    if (prev === "force" && layoutMode === "circle") requestAnimationFrame(() => applyFit("circle"));
  }, [layoutMode, applyFit]);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  useEffect(() => {
    if (layoutMode !== "force") requestAnimationFrame(() => applyFit("circle"));
  }, [graph.nodes, layoutMode, applyFit]);

  useEffect(() => {
    const host = canvasHostRef.current;
    if (!host) return undefined;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr) return;
      setHostSize({ width: Math.max(1, Math.floor(cr.width)), height: Math.max(MIN_CANVAS_HEIGHT, Math.floor(cr.height)) });
    });
    ro.observe(host);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_REPULSION, String(repulsionPercent));
    } catch {
      /* ignore */
    }
  }, [repulsionPercent]);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return undefined;
    const onWheel = (event) => {
      event.preventDefault();
      const rect = el.getBoundingClientRect();
      const mx = event.clientX - rect.left;
      const my = event.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(mx, my, scale, tx, ty);
      const factor = event.deltaY > 0 ? 0.92 : 1.08;
      const newScale = Math.min(Math.max(scale * factor, MIN_SCALE), MAX_SCALE);
      const next = { scale: newScale, tx: mx - world.x * newScale, ty: my - world.y * newScale };
      transformRef.current = next;
      setTransform(next);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const host = canvasHostRef.current;
    if (!canvas || !host) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { w, h } = getViewportDims();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, w, h);
    const positions = getPositionsForFrame();
    positionsRef.current = positions;
    const nodeStyleMap = Object.fromEntries(
      graph.nodes.map((node) => [node.id, { selected: node.id === selectedNodeId, hovered: !selectedNodeId && node.id === input.hoveredNodeId }]),
    );
    const edgeStyleMap = Object.fromEntries(
      graph.edges.map((edge) => [edge.id, { active: edge.id === selectedEdgeId || edge.id === input.hoveredEdgeId }]),
    );
    drawEdges(ctx, graph.edges, nodeById, positions, transformRef.current, edgeStyleMap);
    drawNodes(ctx, graph.nodes, positions, transformRef.current, nodeStyleMap);
    drawLabels(ctx, graph.nodes, graph.edges, positions, transformRef.current, { ...nodeStyleMap, ...edgeStyleMap });
  }, [getPositionsForFrame, getViewportDims, graph.edges, graph.nodes, input.hoveredEdgeId, input.hoveredNodeId, nodeById, selectedEdgeId, selectedNodeId, transform]);

  if (graph.nodes.length === 0) {
    return (
      <Box sx={{ borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a", minHeight: MIN_CANVAS_HEIGHT, display: "flex", alignItems: "center", justifyContent: "center", p: 2 }}>
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No nodes to draw on canvas.</Typography>
      </Box>
    );
  }

  const handleRestart = () => {
    if (layoutMode !== "force" || graph.nodes.length === 0) return;
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    const built = buildSimulationState(graph, { jitterWorld: FORCE_RESTART_JITTER_WORLD });
    setSimLinks(built.links);
    setSimNodes(built.nodes);
    setForceSimRunNonce((n) => n + 1);
    setPhysicsReheatNonce(0);
    setIsSimulationStable(false);
    positionsRef.current = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    applyFit("force");
  };
  const handleUnpinAll = () => {
    fixedNodesRef.current.clear();
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
  };
  const handleCenter = () => {
    if (!selectedNodeId) return;
    const positions = getPositionsForFrame();
    const pw = positions.get(selectedNodeId);
    if (!pw) return;
    const { w, h } = getViewportDims();
    const scale = transformRef.current.scale;
    const next = { scale, tx: w / 2 - pw.x * scale, ty: h / 2 - pw.y * scale };
    transformRef.current = next;
    setTransform(next);
  };

  return (
    <Box ref={wrapRef} component="section" role="region" aria-label="Graph canvas" tabIndex={0} sx={{ width: "100%", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", overflow: "hidden", backgroundColor: "#0a0a0a", outline: "none" }}>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75, px: 1, py: 0.5, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
          <Tooltip title="Canvas controls help">
            <CursorIconButton type="button" aria-label="Canvas controls help">
              <InfoOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          {layoutMode === "force" ? (
            <Tooltip title="Repulsion strength (force simulation spacing)">
              <Box sx={{ width: 128, px: 0.25, cursor: "help" }}>
                <Box sx={{ display: "flex", alignItems: "baseline", gap: 0.5, mb: 0.15 }}>
                  <Typography sx={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.35)", fontFamily: "monospace", letterSpacing: "0.02em" }}>
                    sim
                  </Typography>
                  <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.42)", flex: 1 }}>
                    Repulsion {Math.round(repulsionPercent)}%
                  </Typography>
                </Box>
                <Slider size="small" value={repulsionPercent} min={0} max={100} onChange={(_, v) => setRepulsionPercent(v)} aria-label="Force layout repulsion strength" />
              </Box>
            </Tooltip>
          ) : null}
        </Box>
        <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28 }} />
        <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
          <Tooltip title="Fit graph to view">
            <CursorIconButton type="button" aria-label="Fit graph to view" onClick={() => applyFit("auto")}>
              <FitScreenOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          <Tooltip title="Reset zoom to 1:1 at center">
            <CursorIconButton
              type="button"
              aria-label="Reset zoom to 1:1 at center"
              onClick={() => {
                const { w, h } = getViewportDims();
                const world = screenToWorld(w / 2, h / 2, transformRef.current.scale, transformRef.current.tx, transformRef.current.ty);
                const next = { scale: 1, tx: w / 2 - world.x, ty: h / 2 - world.y };
                transformRef.current = next;
                setTransform(next);
              }}
            >
              <ZoomOutMapOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
          <Tooltip title="Center on selected node">
            <CursorIconButton type="button" aria-label="Center on selected node" onClick={handleCenter} disabled={!selectedNodeId}>
              <CenterFocusStrongOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </Tooltip>
        </Box>
        {layoutMode === "force" ? (
          <>
            <Divider orientation="vertical" flexItem sx={{ borderColor: "rgba(255,255,255,0.08)", alignSelf: "stretch", minHeight: 28 }} />
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.5 }}>
              <Tooltip title="Restart force layout">
                <CursorIconButton type="button" aria-label="Restart force layout" onClick={handleRestart}>
                  <RestartAltOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </Tooltip>
              <Tooltip title="Unpin all dragged nodes">
                <CursorIconButton type="button" aria-label="Unpin all dragged nodes" onClick={handleUnpinAll} disabled={pinnedNodeCount === 0}>
                  <LinkOffOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </Tooltip>
            </Box>
          </>
        ) : null}
        <Box sx={{ flex: 1, minWidth: 8 }} />
      </Box>
      <Box ref={canvasHostRef} sx={{ flex: 1, minHeight: MIN_CANVAS_HEIGHT, position: "relative" }}>
        <canvas
          ref={canvasRef}
          onPointerDown={input.handlePointerDown}
          onPointerMove={input.handlePointerMove}
          onPointerLeave={input.handlePointerLeave}
          onPointerUp={input.handlePointerUp}
          onPointerCancel={input.handlePointerUp}
          style={{ display: "block", width: "100%", height: "100%", cursor: input.canvasCursor, touchAction: "none", verticalAlign: "top" }}
        />
      </Box>
    </Box>
  );
}
