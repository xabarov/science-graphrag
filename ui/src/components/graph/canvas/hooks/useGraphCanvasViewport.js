import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { clampGraphCanvasFitTransform } from "../graphCanvasCamera.js";
import {
  FIT_PADDING,
  MIN_CANVAS_HEIGHT,
  NODE_RADIUS,
} from "../graphCanvasMvpConstants.js";
import { computeFitTransform, computeWorldLayout, screenToWorld } from "../graphCanvasTransform.js";

/**
 * Host sizing, pan/zoom transform, fit-to-graph camera, and related effects for {@link GraphCanvasMvp}.
 *
 * @param {object} opts
 * @param {{ nodes: unknown[], edges: unknown[] }} opts.graph
 * @param {"circle" | "force"} opts.layoutMode
 * @param {number} opts.layoutWorldRadius
 * @param {React.MutableRefObject<import("../../model/graphSimulationAdapter.js").SimNode[]>} opts.simNodesRef
 * @param {React.MutableRefObject<Map<string, { x: number, y: number }>>} opts.positionsRef
 * @param {string} opts.topologySignature
 * @param {() => Map<string, { x: number, y: number }>} opts.getPositionsForFrame
 * @param {number} opts.centerRequestNonce
 * @param {string} opts.centerRequestNodeId
 */
export default function useGraphCanvasViewport({
  graph,
  layoutMode,
  layoutWorldRadius,
  simNodesRef,
  positionsRef,
  topologySignature,
  getPositionsForFrame,
  centerRequestNonce,
  centerRequestNodeId,
}) {
  const canvasHostRef = useRef(null);
  const prevLayoutModeRef = useRef(layoutMode);
  const transformRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const [transform, setTransform] = useState({ scale: 1, tx: 0, ty: 0 });
  const [hostSize, setHostSize] = useState({ width: 0, height: 0 });

  const canvasSize = useMemo(
    () => ({ width: Math.max(1, hostSize.width || 1), height: Math.max(MIN_CANVAS_HEIGHT, hostSize.height || MIN_CANVAS_HEIGHT) }),
    [hostSize.height, hostSize.width],
  );

  const getViewportDims = useCallback(() => {
    const host = canvasHostRef.current;
    return {
      w: Math.max(1, hostSize.width || host?.clientWidth || 1),
      h: Math.max(MIN_CANVAS_HEIGHT, hostSize.height || host?.clientHeight || MIN_CANVAS_HEIGHT),
    };
  }, [hostSize.height, hostSize.width]);

  const applyFit = useCallback(
    /**
     * @param {"auto" | "force" | "circle"} [mode]
     * @param {Map<string, { x: number, y: number }> | null} [seedPositions]
     */
    (mode = "auto", seedPositions = null) => {
      if (graph.nodes.length === 0) return;
      const { w, h } = getViewportDims();
      let positions;
      if (seedPositions instanceof Map && seedPositions.size > 0) {
        positions = seedPositions;
      } else {
        const useForce =
          (mode === "force" || (mode === "auto" && layoutMode === "force")) && simNodesRef.current.length > 0;
        positions = useForce
          ? new Map(simNodesRef.current.map((n) => [n.id, { x: n.x, y: n.y }]))
          : computeWorldLayout(graph.nodes, layoutWorldRadius);
      }
      positionsRef.current = positions;
      const next = clampGraphCanvasFitTransform(computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING));
      transformRef.current = next;
      setTransform(next);
    },
    [getViewportDims, graph.nodes, layoutMode, layoutWorldRadius, positionsRef, simNodesRef],
  );

  const applyFitRef = useRef(applyFit);
  useEffect(() => {
    applyFitRef.current = applyFit;
  }, [applyFit]);

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

  useEffect(() => {
    if (!centerRequestNonce || !centerRequestNodeId) return;
    centerViewportOnNode(centerRequestNodeId);
  }, [centerRequestNonce, centerRequestNodeId, centerViewportOnNode]);

  const handleToolbarResetZoom = useCallback(() => {
    const { w, h } = getViewportDims();
    const world = screenToWorld(w / 2, h / 2, transformRef.current.scale, transformRef.current.tx, transformRef.current.ty);
    const next = { scale: 1, tx: w / 2 - world.x, ty: h / 2 - world.y };
    transformRef.current = next;
    setTransform(next);
  }, [getViewportDims]);

  return {
    canvasHostRef,
    canvasSize,
    transform,
    setTransform,
    transformRef,
    getViewportDims,
    applyFit,
    applyFitRef,
    centerViewportOnNode,
    handleToolbarResetZoom,
  };
}
