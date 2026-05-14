import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { persistRepulsionPercent, readRepulsionPercentStored } from "../graphCanvasMvpStorage.js";
import { localizeAggregatorTitle, localizeEdgeType } from "../../model/graphLocalize.js";
import { useGraphPhysicsPointerBridge } from "../GraphPhysicsPointerBridgeContext.jsx";
import { useGraphCanvasMvpDerivedModel } from "./graphCanvasMvpDerivedModel.js";
import { routeGraphCanvasNodeClick } from "./graphCanvasMvpNodeClickRouting.js";
import { buildActiveForLabelSet, useCanvasLabelMode } from "./useCanvasLabelMode.js";
import useGraphCanvasInput from "./useGraphCanvasInput.js";
import { useGraphCanvasMvpViewActions } from "./useGraphCanvasMvpViewActions.js";
import { useGraphCanvasNodeContextMenu } from "./useGraphCanvasNodeContextMenu.js";
import { useGraphCanvasPaintController } from "./useGraphCanvasPaintController.js";
import useGraphCanvasViewport from "./useGraphCanvasViewport.js";
import { useGraphCanvasWheelZoom } from "./useGraphCanvasWheelZoom.js";
import {
  useGraphCanvasWorldPositions,
  useGraphCanvasWorldSimulationLifecycle,
} from "./useGraphCanvasWorldPositions.js";

/**
 * Orchestration for GraphCanvasMvp: viewport, input, physics, paint, and action handlers.
 * Presentation (MUI Box shell, theme tokens for chrome) stays in GraphCanvasMvp.jsx.
 *
 * Seam map: [`../README.md`](../README.md); canvas hooks compose here → thin `GraphCanvasMvp.jsx` shell.
 */
export function useGraphCanvasMvpController({
  graph,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  layoutMode,
  onCanvasLayoutModeChange,
  onAggregatorExpand,
  searchMatchIds,
  searchQuery,
  centerRequestNonce,
  centerRequestNodeId,
  graphColorBy,
  graphCommunityHulls,
  nodeCommunityMap,
  t,
  appearance,
  canvasBg,
}) {
  const physicsPointerBridge = useGraphPhysicsPointerBridge();
  const physicsPointerBus = physicsPointerBridge?.pointerBus;

  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const positionsRef = useRef(new Map());
  const fixedNodesRef = useRef(new Set());
  const draggedNodePositionRef = useRef(null);

  const [repulsionPercent, setRepulsionPercent] = useState(() => readRepulsionPercentStored());
  const {
    canvasLabelMode,
    setCanvasLabelMode,
    hoverNeighborsLabels,
    setHoverNeighborsLabels,
  } = useCanvasLabelMode();
  const [pinnedNodeCount, setPinnedNodeCount] = useState(0);

  const {
    layoutWorldRadius,
    simNodesRef,
    simNodes,
    setSimNodes,
    simLinks,
    setSimLinks,
    isSimulationStable,
    setIsSimulationStable,
    forceSimRunNonce,
    setForceSimRunNonce,
    physicsReheatNonce,
    setPhysicsReheatNonce,
    getPositionsForFrame,
  } = useGraphCanvasWorldPositions({ graph, layoutMode });

  const {
    topologySignature,
    physicsEpoch,
    simulationSignature,
    repulsionStrength,
    nodeById,
    adjacencyMap,
    searchActive,
    searchMatchSet,
    communityColorStyleMap,
    communityRanks,
    edgeLegendTypes,
  } = useGraphCanvasMvpDerivedModel({
    graph,
    searchMatchIds,
    searchQuery,
    nodeCommunityMap,
    appearance,
    repulsionPercent,
    forceSimRunNonce,
    physicsReheatNonce,
  });

  const resolveEdgeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const resolveNodeCanvasLabel = useCallback(
    (node) => (String(node.nodeKind) === "Aggregator" ? localizeAggregatorTitle(node, t) : null),
    [t],
  );

  const formatCommunityHullLabel = useCallback(
    (rankOneBased, nodeCount) => t("graph.community.hullLabel", { rank: rankOneBased, count: nodeCount }),
    [t],
  );

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

  const viewActions = useGraphCanvasMvpViewActions({
    layoutMode,
    graph,
    applyFit,
    getPositionsForFrame,
    getViewportDims,
    transformRef,
    setTransform,
    selectedNodeId,
    centerViewportOnNode,
    setCanvasLabelMode,
    setHoverNeighborsLabels,
    fixedNodesRef,
    draggedNodePositionRef,
    setPinnedNodeCount,
    setSimNodes,
    setSimLinks,
    simNodesRef,
    positionsRef,
    setForceSimRunNonce,
    setPhysicsReheatNonce,
    setIsSimulationStable,
    canvasLabelMode,
  });

  const {
    showDenseLabelHint,
    dismissDenseHint,
    runFitNodeSubset,
    handleCanvasDoubleClick,
    handleApplyViewPreset,
    handleRestart,
    handleUnpinAll,
    handleCenter,
  } = viewActions;

  const onNodeClick = useCallback(
    (nodeId) => {
      routeGraphCanvasNodeClick({ nodeById, nodeId, onAggregatorExpand, onSelectNode });
    },
    [nodeById, onAggregatorExpand, onSelectNode],
  );

  const onEdgeClick = useCallback((edgeId) => {
    onSelectEdge?.(edgeId);
  }, [onSelectEdge]);

  const onCanvasClick = useCallback(() => {
    onSelectNode?.("");
    onSelectEdge?.("");
  }, [onSelectNode, onSelectEdge]);

  const invokeCanvasRedrawRef = useRef(() => {});
  const invokeCanvasRedraw = useCallback(() => {
    invokeCanvasRedrawRef.current();
  }, []);

  const activeForLabelSetRef = useRef(/** @type {Set<string>} */ (new Set()));

  const input = useGraphCanvasInput({
    canvasRef,
    graph,
    transformRef,
    setTransform,
    onNodeClick,
    onEdgeClick,
    onCanvasClick,
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

  useEffect(() => {
    activeForLabelSetRef.current = activeForLabelSet;
  }, [activeForLabelSet]);

  const { contextMenu, handleCanvasContextMenu, closeContextMenu } = useGraphCanvasNodeContextMenu({
    canvasRef,
    graph,
    getPositionsForFrame,
    transformRef,
    resolveNodeCanvasLabel,
    graphColorBy,
    searchActive,
    searchMatchSet,
    selectedNodeId,
    hoveredNodeId: input.hoveredNodeId,
    canvasLabelMode,
    activeForLabelSet,
  });

  const drawOptsBase = useMemo(
    () => ({
      appearance,
      colorBy: graphColorBy,
      nodeCommunityMap,
      communityColorStyleMap,
    }),
    [appearance, communityColorStyleMap, graphColorBy, nodeCommunityMap],
  );

  useGraphCanvasPaintController({
    invokeCanvasRedrawRef,
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
    drawOptsBase,
    graphCommunityHulls,
    nodeCommunityMap,
    communityRanks,
    formatCommunityHullLabel,
    resolveEdgeLabel,
    resolveNodeCanvasLabel,
    canvasLabelMode,
    activeForLabelSet,
    transform,
  });

  useGraphCanvasWorldSimulationLifecycle({
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
    simNodes,
    simLinks,
    repulsionStrength,
    isSimulationStable,
    physicsEpoch,
    simulationSignature,
    canvasSize,
    physicsPointerBus,
    invokeCanvasRedraw,
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

  return {
    wrapRef,
    canvasRef,
    canvasHostRef,
    input,
    repulsionPercent,
    setRepulsionPercent,
    canvasLabelMode,
    setCanvasLabelMode,
    hoverNeighborsLabels,
    setHoverNeighborsLabels,
    pinnedNodeCount,
    handleToolbarResetZoom,
    applyFit,
    handleRestart,
    handleUnpinAll,
    handleCenter,
    handleApplyViewPreset,
    showDenseLabelHint,
    dismissDenseHint,
    contextMenu,
    closeContextMenu,
    runFitNodeSubset,
    centerViewportOnNode,
    handleCanvasDoubleClick,
    handleCanvasContextMenu,
    edgeLegendTypes,
    onSelectNode,
  };
}
