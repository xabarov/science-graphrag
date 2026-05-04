import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CropFreeIcon from "@mui/icons-material/CropFree";
import MyLocationIcon from "@mui/icons-material/MyLocation";
import { useTheme } from "@mui/material/styles";

import GraphCanvasViewToolbar from "./GraphCanvasViewToolbar.jsx";
import { useI18n } from "../../../i18n/useI18n.js";
import { computeFitTransformForNodeSubset } from "./graphCanvasCamera.js";
import { computeWorldLayout, screenToWorld, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { localizeAggregatorTitle, localizeEdgeType } from "../model/graphLocalize.js";
import { drawCommunityHulls } from "./graphCanvasDrawCommunityHulls.js";
import {
  drawEdges,
  drawLabels,
  drawNodes,
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  NODE_LABEL_ADAPTIVE_MAX_NODES,
  hitTestNodeScreen,
} from "./graphCanvasDraw.js";
import { getGraphLayoutSignature } from "../flow/graphFlowAdapter.js";
import { buildSimulationState } from "../model/graphSimulationAdapter.js";
import { useGraphPhysicsPointerBridge } from "./GraphPhysicsPointerBridgeContext.jsx";
import useGraphCanvasInput from "./hooks/useGraphCanvasInput.js";
import useGraphCanvasViewport from "./hooks/useGraphCanvasViewport.js";
import { useGraphCanvasTopologyReseed } from "./hooks/useGraphCanvasTopologyReseed.js";
import { useScienceGraphForceSimulation } from "../../../hooks/graph/useScienceGraphForceSimulation.js";
import { percentToRepulsion, REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "./physics/communityPalette.js";
import { buildWorldPositionsMapFromSimNodes } from "./graphCanvasSimPositions.js";

const NODE_RADIUS = 12;
const FIT_PADDING = 40;
const MIN_CANVAS_HEIGHT = 280;
const MIN_FIT_SCALE = 0.11;
const FORCE_RESTART_JITTER_WORLD = 56;
const LS_GRAPH_CANVAS_REPULSION = "graphCanvasRepulsionPercent";
const LS_GRAPH_CANVAS_LABEL_MODE = "graphCanvasLabelMode";
const LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS = "graphCanvasLabelHoverNeighbors";
// Legacy key kept for one-shot migration: previously stored only the edge label mode, now used as
// fallback when the new unified key is missing so existing users do not lose their toggle choice.
const LS_GRAPH_CANVAS_LABEL_MODE_LEGACY = "graphCanvasEdgeLabelMode";
const LS_GRAPH_DENSE_LABEL_HINT_DISMISSED = "graphDenseLabelHintDismissed";
const MIN_SCALE = 0.06;
const MAX_SCALE = 8;

const EMPTY_COMMUNITY_MAP = new Map();
const EMPTY_NODE_ID_SET = /** @type {Set<string>} */ (new Set());

/*
 * Force-layout interaction contract (canvas MVP):
 * - In "force" mode, hit-testing reads live positions from simNodesRef via getPositionsForFrame() (Phase B: ref buffer).
 *   If the physics integrator mutates those positions between pointerdown and pointerup, the released click can miss
 *   the intended node; integration is therefore paused for primary pointer sessions on the canvas (see useGraphPhysicsPolicy).
 * - Shell drawer navigation dispatches a short navigation-intent pause so the router can commit before rAF-heavy work resumes.
 * - Add new integration pause reasons only in useGraphPhysicsPolicy (see hook JSDoc), not ad hoc rAF toggles here.
 */

/** @returns {"all" | "interaction" | "adaptive"} */
function readCanvasLabelModeStored() {
  if (typeof window === "undefined") return "adaptive";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_MODE);
    if (v === "all" || v === "interaction" || v === "adaptive") return v;
    const legacy = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_MODE_LEGACY);
    if (legacy === "all" || legacy === "interaction" || legacy === "adaptive") return legacy;
  } catch {
    /* ignore */
  }
  return "adaptive";
}

/** @returns {boolean} */
function readHoverNeighborsLabelsStored() {
  if (typeof window === "undefined") return true;
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS);
    if (v === "0") return false;
    if (v === "1") return true;
  } catch {
    /* ignore */
  }
  return true;
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
  const [canvasLabelMode, setCanvasLabelMode] = useState(() => readCanvasLabelModeStored());
  const [hoverNeighborsLabels, setHoverNeighborsLabels] = useState(() => readHoverNeighborsLabelsStored());
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

  // Undirected 1-hop adjacency for the current topology. Recomputed only when graph.edges changes
  // (O(E)); per-frame neighborhood lookups for label highlighting are then O(deg(node)).
  const adjacencyMap = useMemo(() => {
    /** @type {Map<string, Set<string>>} */
    const map = new Map();
    for (const edge of graph.edges) {
      const s = String(edge.source);
      const t = String(edge.target);
      if (!s || !t) continue;
      let aSet = map.get(s);
      if (!aSet) {
        aSet = new Set();
        map.set(s, aSet);
      }
      let bSet = map.get(t);
      if (!bSet) {
        bSet = new Set();
        map.set(t, bSet);
      }
      aSet.add(t);
      bSet.add(s);
    }
    return map;
  }, [graph.edges]);
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

  const [denseHintDismissed, setDenseHintDismissed] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      return window.sessionStorage.getItem(LS_GRAPH_DENSE_LABEL_HINT_DISMISSED) === "1";
    } catch {
      return false;
    }
  });
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

  // Hit-test reads the live label-active set via this ref to break the cycle:
  //   useGraphCanvasInput → hoveredNodeId → activeForLabelSet → hit-test gating.
  // Updated in a useEffect once activeForLabelSet for the current frame is computed below; the
  // 1-frame lag only affects whether a label hitbox is clickable on the very first hover-into
  // frame, which is acceptable.
  const activeForLabelSetRef = useRef(/** @type {Set<string>} */ (new Set()));

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
    canvasLabelMode,
    activeForLabelSetRef,
    simNodesRef,
    invokeCanvasRedraw,
  });

  // Compute the set of node ids whose labels should be highlighted under "interaction" / dense
  // "adaptive" gating: the explicit selection, the current hover (if no selection), and optionally
  // their direct 1-hop neighbors. Returning a stable empty Set when nothing is active keeps drawLabels
  // and hit-test on a single fast path.
  const activeForLabelSet = useMemo(() => {
    const seeds = [];
    if (selectedNodeId) seeds.push(String(selectedNodeId));
    if (input.hoveredNodeId && input.hoveredNodeId !== selectedNodeId) {
      seeds.push(String(input.hoveredNodeId));
    }
    if (seeds.length === 0) return EMPTY_NODE_ID_SET;
    const out = new Set(seeds);
    if (hoverNeighborsLabels) {
      for (const seed of seeds) {
        const ns = adjacencyMap.get(seed);
        if (!ns) continue;
        for (const id of ns) out.add(id);
      }
    }
    return out;
  }, [adjacencyMap, hoverNeighborsLabels, input.hoveredNodeId, selectedNodeId]);

  // Keep the ref in sync so hit-test callbacks always see the freshest active-for-label set.
  useEffect(() => {
    activeForLabelSetRef.current = activeForLabelSet;
  }, [activeForLabelSet]);

  const [contextMenu, setContextMenu] = useState(/** @type {null | { mouseX: number, mouseY: number, nodeId: string }} */ (null));

  const handleCanvasContextMenu = useCallback(
    (ev) => {
      ev.preventDefault();
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const lx = ev.clientX - rect.left;
      const ly = ev.clientY - rect.top;
      const posMap = getPositionsForFrame();
      const nodeId =
        hitTestNodeScreen(lx, ly, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel, {
          colorBy: graphColorBy,
          nodeCount: graph.nodes.length,
          searchActive,
          searchMatchSet: searchMatchSet instanceof Set ? searchMatchSet : null,
          selectedNodeId,
          hoveredNodeId: input.hoveredNodeId,
          mode: canvasLabelMode,
          activeForLabelSet,
        }) || "";
      if (!nodeId) return;
      setContextMenu({ mouseX: ev.clientX, mouseY: ev.clientY, nodeId });
    },
    [
      activeForLabelSet,
      canvasLabelMode,
      getPositionsForFrame,
      graph.nodes,
      graphColorBy,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      input.hoveredNodeId,
      transformRef,
    ],
  );

  const closeContextMenu = useCallback(() => setContextMenu(null), []);

  const runFitNodeSubset = useCallback(
    (nodeId) => {
      const nid = String(nodeId || "").trim();
      if (!nid || graph.nodes.length === 0) return;
      const { w, h } = getViewportDims();
      const positions = getPositionsForFrame();
      const nextRaw = computeFitTransformForNodeSubset(positions, [nid], w, h, NODE_RADIUS, FIT_PADDING);
      if (!nextRaw) return;
      const next = clampFitTransform(nextRaw);
      transformRef.current = next;
      setTransform(next);
    },
    [getPositionsForFrame, getViewportDims, graph.nodes.length, setTransform, transformRef],
  );

  const showDenseLabelHint =
    canvasLabelMode === "all"
    && !denseHintDismissed
    && (
      graph.edges.length >= EDGE_LABEL_MEGA_DENSE_MIN_EDGES
      || graph.nodes.length > NODE_LABEL_ADAPTIVE_MAX_NODES
    );

  const edgeLegendTypes = useMemo(() => {
    const seen = new Set();
    const out = [];
    for (const e of graph.edges) {
      const t = e?.type != null ? String(e.type) : "";
      if (!t || seen.has(t)) continue;
      seen.add(t);
      out.push(t);
      if (out.length >= 8) break;
    }
    return out;
  }, [graph.edges]);

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
      canvasLabelMode,
      edgeCountForAdaptive: graph.edges.length,
      appearance,
      colorBy: graphColorBy,
      nodeCountForAdaptive: graph.nodes.length,
      searchActive,
      searchMatchSet,
      activeForLabelSet,
    });
  }, [
    activeForLabelSet,
    appearance,
    canvasBg,
    communityColorStyleMap,
    communityRanks,
    formatCommunityHullLabel,
    canvasLabelMode,
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
      window.localStorage.setItem(LS_GRAPH_CANVAS_LABEL_MODE, canvasLabelMode);
    } catch {
      /* ignore */
    }
  }, [canvasLabelMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        LS_GRAPH_CANVAS_LABEL_HOVER_NEIGHBORS,
        hoverNeighborsLabels ? "1" : "0",
      );
    } catch {
      /* ignore */
    }
  }, [hoverNeighborsLabels]);

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
        canvasLabelMode={canvasLabelMode}
        onCanvasLabelModeChange={setCanvasLabelMode}
        hoverNeighborsLabels={hoverNeighborsLabels}
        onHoverNeighborsLabelsChange={setHoverNeighborsLabels}
        onFit={() => applyFit("auto")}
        onResetZoom={handleToolbarResetZoom}
        onCenterSelection={handleCenter}
        centerSelectionDisabled={!selectedNodeId}
        onRestartForce={handleRestart}
        onUnpinAll={handleUnpinAll}
        unpinDisabled={pinnedNodeCount === 0}
      />
      {showDenseLabelHint ? (
        <Alert
          severity="info"
          variant="outlined"
          onClose={() => {
            setDenseHintDismissed(true);
            try {
              window.sessionStorage.setItem(LS_GRAPH_DENSE_LABEL_HINT_DISMISSED, "1");
            } catch {
              /* ignore */
            }
          }}
          sx={{ flexShrink: 0, my: 0.5, fontSize: "0.75rem", py: 0.25 }}
        >
          {t("graph.canvasLabels.denseHint")}{" "}
          <Button size="small" sx={{ ml: 0.5, minWidth: 0 }} onClick={() => setCanvasLabelMode("adaptive")}>
            {t("graph.canvasLabels.switchAdaptive")}
          </Button>
          <Button size="small" sx={{ ml: 0.5, minWidth: 0 }} onClick={() => setCanvasLabelMode("interaction")}>
            {t("graph.canvasLabels.switchInteraction")}
          </Button>
        </Alert>
      ) : null}
      <Menu
        open={Boolean(contextMenu)}
        onClose={closeContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={contextMenu ? { top: contextMenu.mouseY, left: contextMenu.mouseX } : undefined}
      >
        <MenuItem
          onClick={() => {
            const nid = contextMenu?.nodeId;
            closeContextMenu();
            if (!nid) return;
            onSelectNode?.(nid);
            runFitNodeSubset(nid);
          }}
        >
          <CropFreeIcon fontSize="small" sx={{ mr: 1 }} />
          {t("graph.canvas.contextFit")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            const nid = contextMenu?.nodeId;
            closeContextMenu();
            if (!nid) return;
            centerViewportOnNode(nid);
          }}
        >
          <MyLocationIcon fontSize="small" sx={{ mr: 1 }} />
          {t("graph.canvas.contextCenter")}
        </MenuItem>
        <MenuItem
          onClick={() => {
            const nid = contextMenu?.nodeId;
            closeContextMenu();
            if (!nid) return;
            try {
              void navigator.clipboard?.writeText?.(nid);
            } catch {
              /* ignore */
            }
          }}
        >
          <ContentCopyIcon fontSize="small" sx={{ mr: 1 }} />
          {t("graph.canvas.contextCopyId")}
        </MenuItem>
      </Menu>
      <Box ref={canvasHostRef} sx={{ flex: 1, minHeight: MIN_CANVAS_HEIGHT, position: "relative" }}>
        <canvas
          ref={canvasRef}
          onPointerDown={input.handlePointerDown}
          onPointerMove={input.handlePointerMove}
          onPointerLeave={input.handlePointerLeave}
          onPointerUp={input.handlePointerUp}
          onPointerCancel={input.handlePointerUp}
          onDoubleClick={handleCanvasDoubleClick}
          onContextMenu={handleCanvasContextMenu}
          style={{ display: "block", width: "100%", height: "100%", cursor: input.canvasCursor, touchAction: "none", verticalAlign: "top" }}
        />
        {edgeLegendTypes.length > 0 ? (
          <Box
            sx={{
              position: "absolute",
              left: 8,
              bottom: 8,
              maxWidth: "min(240px, 42%)",
              p: 0.75,
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.surface.panel,
              pointerEvents: "none",
            }}
          >
            <Typography sx={{ fontSize: "0.62rem", fontWeight: 600, color: tk.text.muted, mb: 0.25 }}>
              {t("graph.canvas.edgeLegendTitle")}
            </Typography>
            {edgeLegendTypes.map((tp) => (
              <Typography key={tp} sx={{ fontSize: "0.62rem", color: tk.text.secondary, lineHeight: 1.35 }} noWrap>
                {localizeEdgeType({ type: tp, raw: {} }, t)}
              </Typography>
            ))}
          </Box>
        ) : null}
      </Box>
    </Box>
  );
}
