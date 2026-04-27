import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import GraphCanvasViewToolbar from "./GraphCanvasViewToolbar.jsx";
import { useI18n } from "../../i18n/useI18n.js";
import { computeFitTransformForNodeSubset } from "./graphCanvasCamera.js";
import { computeFitTransform, computeWorldLayout, screenToWorld, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { localizeAggregatorTitle, localizeEdgeType } from "./graphLocalize.js";
import { drawCommunityHulls } from "./graphCanvasDrawCommunityHulls.js";
import { drawEdges, drawLabels, drawNodes } from "./graphCanvasDraw.js";
import { getGraphLayoutSignature } from "./graphFlowAdapter.js";
import { buildSimulationState } from "./graphSimulationAdapter.js";
import useGraphCanvasInput from "./hooks/useGraphCanvasInput.js";
import { useGraphCanvasTopologyReseed } from "./hooks/useGraphCanvasTopologyReseed.js";
import { useScienceGraphForceSimulation } from "../../hooks/graph/useScienceGraphForceSimulation.js";
import { percentToRepulsion, REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "./physics/communityPalette.js";

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
  const [edgeLabelMode, setEdgeLabelMode] = useState(() => readEdgeLabelModeStored());
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
      onSelectNode?.(nodeId);
    },
    [nodeById, onAggregatorExpand, onSelectNode],
  );

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
    simNodes,
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
  });

  const applyFitRef = useRef(applyFit);
  useEffect(() => {
    applyFitRef.current = applyFit;
  });

  useEffect(() => {
    const prev = prevLayoutModeRef.current;
    prevLayoutModeRef.current = layoutMode;
    if (prev === layoutMode) return;
    if (prev === "force" && layoutMode === "circle") {
      requestAnimationFrame(() => applyFitRef.current?.("circle"));
    } else if (prev === "circle" && layoutMode === "force") {
      requestAnimationFrame(() => applyFitRef.current?.("force"));
    }
  }, [layoutMode]);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  // Re-fit camera in non-force layouts strictly when topology changes (not when
  // applyFit identity is rebuilt by a viewport resize / details panel toggle).
  useEffect(() => {
    if (layoutMode !== "force") {
      requestAnimationFrame(() => applyFitRef.current?.("circle"));
    }
  }, [topologySignature, layoutMode]);

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
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_EDGE_LABEL_MODE, edgeLabelMode);
    } catch {
      /* ignore */
    }
  }, [edgeLabelMode]);

  const centerViewportOnNode = useCallback(
    (nodeId) => {
      if (!nodeId) return;
      const positions = getPositionsForFrame();
      const pw = positions.get(nodeId);
      if (!pw) return;
      const { w, h } = getViewportDims();
      const scale = transformRef.current.scale;
      const next = { scale, tx: w / 2 - pw.x * scale, ty: h / 2 - pw.y * scale };
      transformRef.current = next;
      setTransform(next);
    },
    [getPositionsForFrame, getViewportDims],
  );

  const handleToolbarResetZoom = useCallback(() => {
    const { w, h } = getViewportDims();
    const world = screenToWorld(w / 2, h / 2, transformRef.current.scale, transformRef.current.tx, transformRef.current.ty);
    const next = { scale: 1, tx: w / 2 - world.x, ty: h / 2 - world.y };
    transformRef.current = next;
    setTransform(next);
  }, [getViewportDims]);

  useEffect(() => {
    if (!centerRequestNonce || !centerRequestNodeId) return;
    centerViewportOnNode(centerRequestNodeId);
  }, [centerRequestNonce, centerRequestNodeId, centerViewportOnNode]);

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
    transform,
  ]);

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
    [getPositionsForFrame, getViewportDims, graph.nodes.length, selectedNodeId, setTransform],
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
