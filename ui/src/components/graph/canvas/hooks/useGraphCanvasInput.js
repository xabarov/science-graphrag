import { useCallback, useRef } from "react";

import { useGraphPhysicsPointerBridge } from "../GraphPhysicsPointerBridgeContext.jsx";
import { graphCanvasInputPointerDown } from "./graphCanvasInput/pointerDown.js";
import { graphCanvasInputPointerMove } from "./graphCanvasInput/pointerMove.js";
import { graphCanvasInputPointerUp } from "./graphCanvasInput/pointerUp.js";
import { useGraphCanvasInputHoverPick } from "./graphCanvasInput/hoverPick.js";

/**
 * Canvas pointer wiring for {@link GraphCanvasMvp}.
 *
 * Composes hover RAF pick, node-drag / pan sessions, and click selection. Submodules live under
 * `./graphCanvasInput/`; seam map in [`../README.md`](../README.md).
 *
 * @param {object} opts
 * @param {import("react").MutableRefObject<import("../../model/graphSimulationAdapter.js").SimNode[]>} opts.simNodesRef Live sim buffer for force mode (mutated on drag).
 * @param {() => void} opts.invokeCanvasRedraw Repaint canvas without waiting for React (physics rAF + drag moves).
 */
export default function useGraphCanvasInput({
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
  bumpPhysicsReheat,
  draggedNodePositionRef,
  fixedNodesRef,
  setPinnedNodeCount,
  resolveNodeCanvasLabel,
  graphColorBy = "type",
  selectedNodeId = "",
  searchActive = false,
  searchMatchSet = null,
  canvasLabelMode = "adaptive",
  activeForLabelSetRef = null,
  simNodesRef,
  invokeCanvasRedraw,
}) {
  const physicsPointerBridge = useGraphPhysicsPointerBridge();
  const pointerBus = physicsPointerBridge?.pointerBus;

  const dragRef = useRef({ active: false, moved: false, startX: 0, startY: 0, startTx: 0, startTy: 0, pointerId: null });
  const nodeDragRef = useRef({ active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null });

  const {
    hoveredNodeId,
    hoveredEdgeId,
    canvasCursor,
    setHoveredNodeId,
    setHoveredEdgeId,
    setCanvasCursor,
    queueHoverPick,
    clearHover,
  } = useGraphCanvasInputHoverPick({
    canvasRef,
    dragRef,
    nodeDragRef,
    getPositionsForFrame,
    graph,
    transformRef,
    resolveNodeCanvasLabel,
    graphColorBy,
    searchActive,
    searchMatchSet,
    selectedNodeId,
    canvasLabelMode,
    activeForLabelSetRef,
  });

  const handlePointerDown = useCallback(
    (ev) => {
      graphCanvasInputPointerDown(
        {
          canvasRef,
          simNodesRef,
          getPositionsForFrame,
          graph,
          transformRef,
          resolveNodeCanvasLabel,
          graphColorBy,
          hoveredNodeId,
          searchActive,
          searchMatchSet,
          selectedNodeId,
          canvasLabelMode,
          activeForLabelSetRef,
          layoutMode,
          onCanvasLayoutModeChange,
          draggedNodePositionRef,
          nodeDragRef,
          dragRef,
          invokeCanvasRedraw,
          pointerBus,
        },
        ev,
      );
    },
    [
      activeForLabelSetRef,
      canvasLabelMode,
      canvasRef,
      draggedNodePositionRef,
      getPositionsForFrame,
      graph,
      graphColorBy,
      hoveredNodeId,
      invokeCanvasRedraw,
      layoutMode,
      onCanvasLayoutModeChange,
      pointerBus,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      simNodesRef,
      transformRef,
    ],
  );

  const handlePointerMove = useCallback(
    (ev) => {
      graphCanvasInputPointerMove(
        {
          canvasRef,
          nodeDragRef,
          dragRef,
          draggedNodePositionRef,
          simNodesRef,
          transformRef,
          setTransform,
          setIsSimulationStable,
          bumpPhysicsReheat,
          setHoveredNodeId,
          setHoveredEdgeId,
          setCanvasCursor,
          queueHoverPick,
          invokeCanvasRedraw,
        },
        ev,
      );
    },
    [
      bumpPhysicsReheat,
      canvasRef,
      draggedNodePositionRef,
      invokeCanvasRedraw,
      queueHoverPick,
      setCanvasCursor,
      setHoveredEdgeId,
      setHoveredNodeId,
      setIsSimulationStable,
      setTransform,
      simNodesRef,
      transformRef,
    ],
  );

  const handlePointerLeave = useCallback(() => {
    clearHover();
  }, [clearHover]);

  const handlePointerUp = useCallback(
    (ev) => {
      graphCanvasInputPointerUp(
        {
          canvasRef,
          nodeDragRef,
          dragRef,
          draggedNodePositionRef,
          simNodesRef,
          fixedNodesRef,
          isSimulationStable,
          setIsSimulationStable,
          bumpPhysicsReheat,
          setSimNodes,
          setPinnedNodeCount,
          invokeCanvasRedraw,
          getPositionsForFrame,
          graph,
          transformRef,
          resolveNodeCanvasLabel,
          graphColorBy,
          hoveredNodeId,
          searchActive,
          searchMatchSet,
          selectedNodeId,
          canvasLabelMode,
          activeForLabelSetRef,
          onNodeClick,
          onEdgeClick,
          onCanvasClick,
          queueHoverPick,
          pointerBus,
        },
        ev,
      );
    },
    [
      activeForLabelSetRef,
      bumpPhysicsReheat,
      canvasLabelMode,
      canvasRef,
      draggedNodePositionRef,
      fixedNodesRef,
      getPositionsForFrame,
      graph,
      graphColorBy,
      hoveredNodeId,
      invokeCanvasRedraw,
      isSimulationStable,
      onCanvasClick,
      onEdgeClick,
      onNodeClick,
      pointerBus,
      queueHoverPick,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      setIsSimulationStable,
      setPinnedNodeCount,
      setSimNodes,
      simNodesRef,
      transformRef,
    ],
  );

  return {
    hoveredNodeId,
    hoveredEdgeId,
    canvasCursor,
    queueHoverPick,
    handlePointerDown,
    handlePointerMove,
    handlePointerLeave,
    handlePointerUp,
    clearHover,
  };
}
