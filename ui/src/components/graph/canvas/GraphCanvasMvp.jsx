import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import GraphCanvasViewToolbar from "./GraphCanvasViewToolbar.jsx";
import { useI18n } from "../../i18n/useI18n.js";
import { computeFitTransformForNodeSubset } from "./graphCanvasCamera.js";
import { computeWorldLayout, screenToWorld, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { localizeAggregatorTitle, localizeEdgeType } from "./graphLocalize.js";
import { drawCommunityHulls } from "./graphCanvasDrawCommunityHulls.js";
import { drawEdges, drawLabels, drawNodes } from "./graphCanvasDraw.js";
import { getGraphLayoutSignature } from "./graphFlowAdapter.js";
import { buildSimulationState } from "./graphSimulationAdapter.js";
import { useGraphPhysicsPointerBridge } from "./GraphPhysicsPointerBridgeContext.jsx";
import useGraphCanvasInput from "./hooks/useGraphCanvasInput.js";
import useGraphCanvasViewport from "./hooks/useGraphCanvasViewport.js";
import { useGraphCanvasTopologyReseed } from "./hooks/useGraphCanvasTopologyReseed.js";
import { useScienceGraphForceSimulation } from "../../hooks/graph/useScienceGraphForceSimulation.js";
import { percentToRepulsion, REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "./physics/communityPalette.js";
import { buildWorldPositionsMapFromSimNodes } from "./graphCanvasSimPositions.js";

const NODE_RADIUS = 12;
const FIT_PADDING = 40;
const MIN_CANVAS_HEIGHT = 280;
const MIN_FIT_SCALE = 0.11;
const FORCE_RESTART_JITTER_WORLD = 56;
const LS_GRAPH_CANVAS_REPULSION = "graphCanvasRepulsionPercent";
const LS_GRAPH_CANVAS_EDGE_LABEL_MODE = "graphCanvasEdgeLabelMode";
const MIN_SCALE = 0.06;
const MAX_SCALE = 8;

const EMPTY_COMMUNITY_MAP = new Map();

/*
 * Force-layout interaction contract (canvas MVP):
 * - In "force" mode, hit-testing reads live positions from simNodesRef via getPositionsForFrame() (Phase B: ref buffer).
 *   If the physics integrator mutates those positions between pointerdown and pointerup, the released click can miss
 *   the intended node; integration is therefore paused for primary pointer sessions on the canvas (see useGraphPhysicsPolicy).
 * - Shell drawer navigation dispatches a short navigation-intent pause so the router can commit before rAF-heavy work resumes.
 */

/** @returns {"all" | "interaction" | "adaptive"} */
function readEdgeLabelModeStored() {
  if (typeof window === "undefined") return "adaptive";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_EDGE_LABEL_MODE);
    if (v === "all" || v === "interaction" || v === "adaptive") return v;
  } catch {
    /* ignore */
  }
  return "adaptive";
}

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
  /** When non-empty and query is active, nodes not in this Set are drawn dimmed (local find). */
  searchMatchIds = null,
  /** Non-empty trimmed string enables search dimming on canvas. */
  searchQuery = "",
  /** Increment to center viewport on this node id without requiring prior selection. */
  centerRequestNonce = 0,
  centerRequestNodeId = "",
  graphColorBy = "type",
  onGraphColorByChange,
  graphCommunityHulls = false,
  onGraphCommunityHullsChange,
  nodeCommunityMap = EMPTY_COMMUNITY_MAP,
}) {
  const { t } = useI18n();
  const theme = useTheme();
  const tk = theme.appTokens;
  const appearance = theme.palette.mode === "light" ? "light" : "dark";
  const canvasBg = tk.surface.app;
  const resolveEdgeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const resolveNodeCanvasLabel = useCallback(
    (node) => (String(node.nodeKind) === "Aggregator" ? localizeAggregatorTitle(node, t) : null),
    [t],
  );

  const formatCommunityHullLabel = useCallback(
    (rankOneBased, nodeCount) => t("graph.community.hullLabel", { rank: rankOneBased, count: nodeCount }),
    [t],
  );

  const physicsPointerBridge = useGraphPhysicsPointerBridge();
  const physicsPointerBus = physicsPointerBridge?.pointerBus;

  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const positionsRef = useRef(new Map());
  const fixedNodesRef = useRef(new Set());
  const draggedNodePositionRef = useRef(null);
  const simNodesRef = useRef([]);

  const [simNodes, setSimNodes] = useState([]);
  const [simLinks, setSimLinks] = useState([]);
  const [isSimulationStable, setIsSimulationStable] = useState(false);
  const [repulsionPercent, setRepulsionPercent] = useState(() => readRepulsionPercentStored());
  const [edgeLabelMode, setEdgeLabelMode] = useState(() => readEdgeLabelModeStored());
  const [forceSimRunNonce, setForceSimRunNonce] = useState(0);
  const [physicsReheatNonce, setPhysicsReheatNonce] = useState(0);
  const [pinnedNodeCount, setPinnedNodeCount] = useState(0);

  const topologySignature = useMemo(() => getGraphLayoutSignature({ nodes: graph.nodes, edges: graph.edges }), [graph.nodes, graph.edges]);
  const physicsEpoch = useMemo(
    () => `${forceSimRunNonce}|${physicsReheatNonce}`,
    [forceSimRunNonce, physicsReheatNonce],
  );
  const simulationSignature = useMemo(
    () => `${topologySignature}|${physicsEpoch}`,
    [topologySignature, physicsEpoch],
  );
  const repulsionStrength = useMemo(() => percentToRepulsion(repulsionPercent), [repulsionPercent]);
  const layoutWorldRadius = useMemo(() => worldRadiusForNodeCount(graph.nodes.length), [graph.nodes.length]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const searchTrim = useMemo(() => ((searchQuery != null && String(searchQuery).trim()) || ""), [searchQuery]);
  const searchActive = searchTrim.length > 0;
  const searchMatchSet = useMemo(() => {
    if (searchMatchIds instanceof Set) return searchMatchIds;
    if (Array.isArray(searchMatchIds)) return new Set(searchMatchIds);
    return new Set();
  }, [searchMatchIds]);

  const communityColorStyleMap = useMemo(
    () => buildCommunityColorStyleMap(nodeCommunityMap, appearance),
    [nodeCommunityMap, appearance],
  );

  const communityRanks = useMemo(() => {
    const sorted = sortedCommunitiesByCount(nodeCommunityMap);
    const m = new Map();
    sorted.forEach((row, i) => m.set(row.id, i));
    return m;
  }, [nodeCommunityMap]);

  useEffect(() => {
    simNodesRef.current = simNodes;
  }, [simNodes]);

  const getPositionsForFrame = useCallback(() => {
    if (layoutMode === "force" && simNodesRef.current.length > 0) {
      return buildWorldPositionsMapFromSimNodes(simNodesRef.current);
    }
    return computeWorldLayout(graph.nodes, layoutWorldRadius);
  }, [graph.nodes, layoutMode, layoutWorldRadius]);

  const viewport = useGraphCanvasViewport({
    graph,
    layoutMode,
    layoutWorldRadius,
    simNodesRef,
    positionsRef,
    topologySignature,
    getPositionsForFrame,
    centerRequestNonce,
    centerRequestNodeId,
  });

  const {
    canvasHostRef,
    canvasSize,
    transform,
    setTransform,
    transformRef,
    getViewportDims,
    applyFit,
    centerViewportOnNode,
    handleToolbarResetZoom,
  } = viewport;

  const onNodeClick = useCallback(
    (nodeId) => {
      const clickedNode = nodeById.get(nodeId);
      if (clickedNode?.nodeKind === "Aggregator") {
        const expandUrl = clickedNode.raw?.aggregation_hints?.expand_endpoint;
        if (expandUrl) onAggregatorExpand?.(clickedNode, expandUrl);
        return;
      }
      onSelectNode?.(nodeId);
    },
    [nodeById, onAggregatorExpand, onSelectNode],
  );

  /** Canvas paint invoked from physics rAF and pointer-drag without waiting on React commit. */
  const invokeCanvasRedrawRef = useRef(() => {});
  const invokeCanvasRedraw = useCallback(() => {
    invokeCanvasRedrawRef.current();
  }, []);

  const input = useGraphCanvasInput({
    canvasRef,
    graph,
    transformRef,
    setTransform,
    onNodeClick,
    onEdgeClick: (edgeId) => {
      onSelectEdge?.(edgeId);
    },
    onCanvasClick: () => {
      onSelectNode?.("");
      onSelectEdge?.("");
    },
    getPositionsForFrame,
    layoutMode,
    onCanvasLayoutModeChange,
    setSimNodes,
    isSimulationStable,
    setIsSimulationStable,
    bumpPhysicsReheat: () => setPhysicsReheatNonce((n) => n + 1),
    draggedNodePositionRef,
    fixedNodesRef,
    setPinnedNodeCount,
    resolveNodeCanvasLabel,
    graphColorBy,
    selectedNodeId,
    searchActive,
    searchMatchSet,
    simNodesRef,
    invokeCanvasRedraw,
  });

  const paintGraphCanvas = useCallback(() => {
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
    ctx.fillStyle = canvasBg;
    ctx.fillRect(0, 0, w, h);
    const positions = getPositionsForFrame();
    positionsRef.current = positions;
    const nodeStyleMap = Object.fromEntries(
      graph.nodes.map((node) => [
        node.id,
        {
          selected: node.id === selectedNodeId,
          hovered: !selectedNodeId && node.id === input.hoveredNodeId,
          searchDim: searchActive && !searchMatchSet.has(node.id),
        },
      ]),
    );
    const edgeStyleMap = Object.fromEntries(
      graph.edges.map((edge) => [edge.id, { active: edge.id === selectedEdgeId || edge.id === input.hoveredEdgeId }]),
    );
    const drawOpts = {
      appearance,
      colorBy: graphColorBy,
      nodeCommunityMap,
      communityColorStyleMap,
    };
    if (graphColorBy === "community" && graphCommunityHulls) {
      drawCommunityHulls(ctx, graph.nodes, positions, transformRef.current, nodeCommunityMap, communityColorStyleMap, {
        appearance,
        communityRanks,
        formatHullLabel: formatCommunityHullLabel,
      });
    }
    drawEdges(ctx, graph.edges, nodeById, positions, transformRef.current, edgeStyleMap, drawOpts);
    drawNodes(ctx, graph.nodes, positions, transformRef.current, nodeStyleMap, drawOpts);
    drawLabels(ctx, graph.nodes, graph.edges, positions, transformRef.current, { ...nodeStyleMap, ...edgeStyleMap }, {
      resolveEdgeLabel,
      resolveNodeCanvasLabel,
      edgeLabelMode,
      edgeCountForAdaptive: graph.edges.length,
      appearance,
      colorBy: graphColorBy,
      nodeCountForAdaptive: graph.nodes.length,
      searchActive,
      searchMatchSet,
    });
  }, [
    appearance,
    canvasBg,
    communityColorStyleMap,
    communityRanks,
    formatCommunityHullLabel,
    edgeLabelMode,
    graphColorBy,
    graphCommunityHulls,
    nodeCommunityMap,
    getPositionsForFrame,
    getViewportDims,
    graph.edges,
    graph.nodes,
    input.hoveredEdgeId,
    input.hoveredNodeId,
    nodeById,
    resolveEdgeLabel,
    resolveNodeCanvasLabel,
    searchActive,
    searchMatchSet,
    selectedEdgeId,
    selectedNodeId,
    canvasHostRef,
    transformRef,
  ]);

  useLayoutEffect(() => {
    invokeCanvasRedrawRef.current = paintGraphCanvas;
  }, [paintGraphCanvas]);

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
    topologySignature,
    physicsEpoch,
    simulationSignature,
    physicsPointerBus,
    simNodesRef,
    invokeCanvasRedraw,
  );

  useGraphCanvasTopologyReseed({
    topologySignature,
    layoutMode,
    graph,
    applyFit,
    setSimNodes,
    setSimLinks,
    setPinnedNodeCount,
    fixedNodesRef,
    draggedNodePositionRef,
    setIsSimulationStable,
    setForceSimRunNonce,
    setPhysicsReheatNonce,
    positionsRef,
    simNodesRef,
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_REPULSION, String(repulsionPercent));
    } catch {
      /* ignore */
    }
  }, [repulsionPercent]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_EDGE_LABEL_MODE, edgeLabelMode);
    } catch {
      /* ignore */
    }
  }, [edgeLabelMode]);

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
    // Mount once: wheel handler reads latest transform via transformRef.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable canvas + ref indirection
  }, []);

  useEffect(() => {
    paintGraphCanvas();
  }, [paintGraphCanvas, transform]);

  const handleCanvasDoubleClick = useCallback(
    (ev) => {
      ev.preventDefault();
      if (graph.nodes.length === 0 || !selectedNodeId) return;
      const { w, h } = getViewportDims();
      const positions = getPositionsForFrame();
      const nextRaw = computeFitTransformForNodeSubset(positions, [selectedNodeId], w, h, NODE_RADIUS, FIT_PADDING);
      if (!nextRaw) return;
      const next = clampFitTransform(nextRaw);
      transformRef.current = next;
      setTransform(next);
    },
    [getPositionsForFrame, getViewportDims, graph.nodes.length, selectedNodeId, setTransform, transformRef],
  );

  if (graph.nodes.length === 0) {
    return (
      <Box sx={{ borderRadius: "6px", border: `1px solid ${tk.border.default}`, backgroundColor: tk.surface.panel, minHeight: MIN_CANVAS_HEIGHT, display: "flex", alignItems: "center", justifyContent: "center", p: 2 }}>
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("graph.canvas.empty")}</Typography>
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
    simNodesRef.current = built.nodes;
    setSimNodes(built.nodes);
    setForceSimRunNonce((n) => n + 1);
    setPhysicsReheatNonce(0);
    setIsSimulationStable(false);
    const seed = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    positionsRef.current = seed;
    applyFit("force", seed);
  };
  const handleUnpinAll = () => {
    fixedNodesRef.current.clear();
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
  };
  const handleCenter = () => centerViewportOnNode(selectedNodeId);

  return (
    <Box
      ref={wrapRef}
      component="section"
      role="region"
      aria-label={t("graph.canvas.regionAria")}
      tabIndex={0}
      sx={{ width: "100%", flex: 1, minHeight: 0, display: "flex", flexDirection: "column", borderRadius: "6px", border: `1px solid ${tk.border.default}`, overflow: "hidden", backgroundColor: tk.surface.panel, outline: "none" }}
    >
      <GraphCanvasViewToolbar
        t={t}
        layoutMode={layoutMode}
        repulsionPercent={repulsionPercent}
        onRepulsionChange={setRepulsionPercent}
        graphColorBy={graphColorBy}
        onGraphColorByChange={onGraphColorByChange || (() => {})}
        graphCommunityHulls={graphCommunityHulls}
        onGraphCommunityHullsChange={onGraphCommunityHullsChange || (() => {})}
        edgeLabelMode={edgeLabelMode}
        onEdgeLabelModeChange={setEdgeLabelMode}
        onFit={() => applyFit("auto")}
        onResetZoom={handleToolbarResetZoom}
        onCenterSelection={handleCenter}
        centerSelectionDisabled={!selectedNodeId}
        onRestartForce={handleRestart}
        onUnpinAll={handleUnpinAll}
        unpinDisabled={pinnedNodeCount === 0}
      />
      <Box ref={canvasHostRef} sx={{ flex: 1, minHeight: MIN_CANVAS_HEIGHT, position: "relative" }}>
        <canvas
          ref={canvasRef}
          onPointerDown={input.handlePointerDown}
          onPointerMove={input.handlePointerMove}
          onPointerLeave={input.handlePointerLeave}
          onPointerUp={input.handlePointerUp}
          onPointerCancel={input.handlePointerUp}
          onDoubleClick={handleCanvasDoubleClick}
          style={{ display: "block", width: "100%", height: "100%", cursor: input.canvasCursor, touchAction: "none", verticalAlign: "top" }}
        />
      </Box>
    </Box>
  );
}
