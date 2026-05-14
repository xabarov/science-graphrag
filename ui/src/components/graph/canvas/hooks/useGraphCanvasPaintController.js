import { useCallback, useEffect, useLayoutEffect } from "react";

import { paintGraphCanvasMvpFrame } from "../graphCanvasMvpFrame.js";

/**
 * Canvas repaint bridge: stable invoke ref for RAF physics + transform-driven full paint.
 *
 * @param {object} params
 * @param {import("react").RefObject<HTMLCanvasElement | null>} params.canvasRef
 * @param {import("react").RefObject<HTMLElement | null>} params.canvasHostRef
 * @param {() => { w: number, h: number }} params.getViewportDims
 * @param {string} params.canvasBg
 * @param {() => Map<string, { x: number, y: number }>} params.getPositionsForFrame
 * @param {import("react").MutableRefObject<Map<string, { x: number, y: number }>>} params.positionsRef
 * @param {import("react").MutableRefObject<{ scale: number, tx: number, ty: number }>} params.transformRef
 * @param {object} params.graph
 * @param {Map<string, object>} params.nodeById
 * @param {string} params.selectedNodeId
 * @param {string} params.selectedEdgeId
 * @param {string | null | undefined} params.hoveredNodeId
 * @param {string | null | undefined} params.hoveredEdgeId
 * @param {boolean} params.searchActive
 * @param {Set<string>} params.searchMatchSet
 * @param {object} params.drawOptsBase
 * @param {boolean} params.graphCommunityHulls
 * @param {Map<string, unknown>} params.nodeCommunityMap
 * @param {Map<string, number>} params.communityRanks
 * @param {(rankOneBased: number, nodeCount: number) => string} params.formatCommunityHullLabel
 * @param {(e: object) => string} params.resolveEdgeLabel
 * @param {(node: object) => string | null} params.resolveNodeCanvasLabel
 * @param {"all"|"interaction"|"adaptive"} params.canvasLabelMode
 * @param {Set<string>} params.activeForLabelSet
 * @param {{ scale: number, tx: number, ty: number }} params.transform
 * @param {import("react").MutableRefObject<() => void>} params.invokeCanvasRedrawRef
 */
export function useGraphCanvasPaintController({
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
  hoveredNodeId,
  hoveredEdgeId,
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
}) {
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
      hoveredNodeId,
      hoveredEdgeId,
      searchActive,
      searchMatchSet,
      drawOptsBase: {
        appearance: drawOptsBase.appearance,
        colorBy: drawOptsBase.colorBy,
        nodeCommunityMap: drawOptsBase.nodeCommunityMap,
        communityColorStyleMap: drawOptsBase.communityColorStyleMap,
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
    canvasBg,
    canvasHostRef,
    communityRanks,
    formatCommunityHullLabel,
    canvasLabelMode,
    drawOptsBase.appearance,
    drawOptsBase.colorBy,
    drawOptsBase.communityColorStyleMap,
    drawOptsBase.nodeCommunityMap,
    graphCommunityHulls,
    nodeCommunityMap,
    getPositionsForFrame,
    getViewportDims,
    graph,
    hoveredEdgeId,
    hoveredNodeId,
    nodeById,
    resolveEdgeLabel,
    resolveNodeCanvasLabel,
    searchActive,
    searchMatchSet,
    selectedEdgeId,
    selectedNodeId,
    canvasRef,
    transformRef,
    positionsRef,
  ]);

  useLayoutEffect(() => {
    invokeCanvasRedrawRef.current = paintGraphCanvas;
  }, [invokeCanvasRedrawRef, paintGraphCanvas]);

  useEffect(() => {
    paintGraphCanvas();
  }, [paintGraphCanvas, transform]);
}
