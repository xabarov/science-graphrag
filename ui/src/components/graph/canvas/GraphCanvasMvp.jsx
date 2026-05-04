import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

import GraphCanvasDenseLabelHint from "./GraphCanvasDenseLabelHint.jsx";
import GraphCanvasEmptyState from "./GraphCanvasEmptyState.jsx";
import GraphCanvasEdgeTypeLegend from "./GraphCanvasEdgeTypeLegend.jsx";
import GraphCanvasNodeContextMenu from "./GraphCanvasNodeContextMenu.jsx";
import GraphCanvasViewportControls from "./GraphCanvasViewportControls.jsx";
import GraphCanvasViewToolbar from "./GraphCanvasViewToolbar.jsx";
import {
  FIT_PADDING,
  FORCE_RESTART_JITTER_WORLD,
  MIN_CANVAS_HEIGHT,
  MIN_FIT_SCALE,
  NODE_RADIUS,
} from "./graphCanvasMvpConstants.js";
import {
  persistDenseLabelHintDismissed,
  persistRepulsionPercent,
  readDenseLabelHintDismissed,
  readRepulsionPercentStored,
} from "./graphCanvasMvpStorage.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { computeFitTransformForNodeSubset } from "./graphCanvasCamera.js";
import { computeWorldLayout, worldRadiusForNodeCount } from "./graphCanvasTransform.js";
import { localizeAggregatorTitle, localizeEdgeType } from "../model/graphLocalize.js";
import { paintGraphCanvasMvpFrame } from "./graphCanvasMvpFrame.js";
import {
  EDGE_LABEL_MEGA_DENSE_MIN_EDGES,
  NODE_LABEL_ADAPTIVE_MAX_NODES,
  hitTestNodeScreen,
} from "./graphCanvasDraw.js";
import { getGraphLayoutSignature } from "../flow/graphFlowAdapter.js";
import { buildSimulationState } from "../model/graphSimulationAdapter.js";
import { useGraphPhysicsPointerBridge } from "./GraphPhysicsPointerBridgeContext.jsx";
import useGraphCanvasInput from "./hooks/useGraphCanvasInput.js";
import useGraphCanvasViewport from "./hooks/useGraphCanvasViewport.js";
import { buildActiveForLabelSet, useCanvasLabelMode } from "./hooks/useCanvasLabelMode.js";
import { useGraphAdjacency } from "./hooks/useGraphAdjacency.js";
import { useGraphCanvasWheelZoom } from "./hooks/useGraphCanvasWheelZoom.js";
import { useGraphCanvasTopologyReseed } from "./hooks/useGraphCanvasTopologyReseed.js";
import { useScienceGraphForceSimulation } from "../../../hooks/graph/useScienceGraphForceSimulation.js";
import { percentToRepulsion } from "./physics/simConstants.js";
import { buildCommunityColorStyleMap, sortedCommunitiesByCount } from "./physics/communityPalette.js";
import { buildWorldPositionsMapFromSimNodes } from "./graphCanvasSimPositions.js";
const EMPTY_COMMUNITY_MAP = new Map();

/*
 * Force-layout interaction contract (canvas MVP):
 * - In "force" mode, hit-testing reads live positions from simNodesRef via getPositionsForFrame() (Phase B: ref buffer).
 *   If the physics integrator mutates those positions between pointerdown and pointerup, the released click can miss
 *   the intended node; integration is therefore paused for primary pointer sessions on the canvas (see useGraphPhysicsPolicy).
 * - Shell drawer navigation dispatches a short navigation-intent pause so the router can commit before rAF-heavy work resumes.
 * - Add new integration pause reasons only in useGraphPhysicsPolicy (see hook JSDoc), not ad hoc rAF toggles here.
 */

function clampFitTransform(fit) {
  return { ...fit, scale: Math.max(fit.scale, MIN_FIT_SCALE) };
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
  const {
    canvasLabelMode,
    setCanvasLabelMode,
    hoverNeighborsLabels,
    setHoverNeighborsLabels,
  } = useCanvasLabelMode();
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

  const adjacencyMap = useGraphAdjacency(graph.edges);
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

  const [denseHintDismissed, setDenseHintDismissed] = useState(() => readDenseLabelHintDismissed());
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

  const activeForLabelSetRef = useRef(/** @type {Set<string>} */ (new Set()));

  // Hit-test reads the live label-active set via this ref to break the cycle:
  //   useGraphCanvasInput → hoveredNodeId → activeForLabelSet → hit-test gating.
  // Updated in a useEffect once activeForLabelSet for the current frame is computed below; the
  // 1-frame lag only affects whether a label hitbox is clickable on the very first hover-into
  // frame, which is acceptable.
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

  const activeForLabelSet = useMemo(
    () => buildActiveForLabelSet(adjacencyMap, selectedNodeId, input.hoveredNodeId, hoverNeighborsLabels),
    [adjacencyMap, hoverNeighborsLabels, input.hoveredNodeId, selectedNodeId],
  );

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
    paintGraphCanvasMvpFrame({
      canvasRef,
      canvasHostRef,
      getViewportDims,
      canvasBg,
      getPositionsForFrame,
      positionsRef,
      transformRef,
      graph,
      nodeById,
      selectedNodeId,
      selectedEdgeId,
      hoveredNodeId: input.hoveredNodeId,
      hoveredEdgeId: input.hoveredEdgeId,
      searchActive,
      searchMatchSet,
      drawOptsBase: {
        appearance,
        colorBy: graphColorBy,
        nodeCommunityMap,
        communityColorStyleMap,
      },
      graphCommunityHulls,
      nodeCommunityMap,
      communityRanks,
      formatHullLabel: formatCommunityHullLabel,
      resolveEdgeLabel,
      resolveNodeCanvasLabel,
      canvasLabelMode,
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
    graph,
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
    persistRepulsionPercent(repulsionPercent);
  }, [repulsionPercent]);

  useGraphCanvasWheelZoom({
    canvasRef,
    transformRef,
    setTransform,
    enabled: graph.nodes.length > 0,
  });

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

  const handleApplyViewPreset = useCallback(
    (preset) => {
      setHoverNeighborsLabels(true);
      if (preset === "overview") {
        setCanvasLabelMode("interaction");
      } else {
        setCanvasLabelMode("adaptive");
      }
    },
    [setCanvasLabelMode, setHoverNeighborsLabels],
  );

  if (graph.nodes.length === 0) {
    return <GraphCanvasEmptyState tk={tk} message={t("graph.canvas.empty")} />;
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
        hideViewControls
        onApplyViewPreset={handleApplyViewPreset}
      />
      {showDenseLabelHint ? (
        <GraphCanvasDenseLabelHint
          message={t("graph.canvasLabels.denseHint")}
          switchAdaptiveLabel={t("graph.canvasLabels.switchAdaptive")}
          switchInteractionLabel={t("graph.canvasLabels.switchInteraction")}
          onDismiss={() => {
            setDenseHintDismissed(true);
            persistDenseLabelHintDismissed();
          }}
          onSwitchAdaptive={() => setCanvasLabelMode("adaptive")}
          onSwitchInteraction={() => setCanvasLabelMode("interaction")}
        />
      ) : null}
      <GraphCanvasNodeContextMenu
        open={Boolean(contextMenu)}
        anchor={contextMenu}
        onClose={closeContextMenu}
        onFit={(nid) => runFitNodeSubset(nid)}
        onCenter={(nid) => centerViewportOnNode(nid)}
        onSelectNode={(nid) => onSelectNode?.(nid)}
        labels={{
          fit: t("graph.canvas.contextFit"),
          center: t("graph.canvas.contextCenter"),
          copyId: t("graph.canvas.contextCopyId"),
        }}
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
          onContextMenu={handleCanvasContextMenu}
          style={{ display: "block", width: "100%", height: "100%", cursor: input.canvasCursor, touchAction: "none", verticalAlign: "top" }}
        />
        <GraphCanvasViewportControls
          t={t}
          onFit={() => applyFit("auto")}
          onResetZoom={handleToolbarResetZoom}
          onCenterSelection={handleCenter}
          centerSelectionDisabled={!selectedNodeId}
        />
        <GraphCanvasEdgeTypeLegend
          edgeTypes={edgeLegendTypes}
          title={t("graph.canvas.edgeLegendTitle")}
          formatEdgeType={(tp) => localizeEdgeType({ type: tp, raw: {} }, t)}
          borderColor={tk.border.default}
          panelBg={tk.surface.panel}
          textMuted={tk.text.muted}
          textSecondary={tk.text.secondary}
        />
      </Box>
    </Box>
  );
}
