import { useCallback, useEffect, useRef, useState } from "react";

import { hitTestClosestEdgeId, hitTestNodeScreen } from "../../graphCanvasDraw.js";
import { buildNodeHitTestScreenOpts } from "./hitTestContext.js";

/**
 * RAF-coalesced hover hit-testing. Skips work while pan or node-drag is active and moved.
 *
 * @param {object} p
 * @param {import("react").RefObject<HTMLCanvasElement | null>} p.canvasRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean }>} p.dragRef
 * @param {import("react").MutableRefObject<{ active: boolean; moved: boolean }>} p.nodeDragRef
 * @param {() => Map<string, { x: number; y: number }>} p.getPositionsForFrame
 * @param {{ nodes: unknown[]; edges: unknown[] }} p.graph
 * @param {import("react").MutableRefObject<{ scale: number; tx: number; ty: number }>} p.transformRef
 * @param {(node: unknown) => string | null} p.resolveNodeCanvasLabel
 * @param {string} p.graphColorBy
 * @param {boolean} p.searchActive
 * @param {unknown} p.searchMatchSet
 * @param {string} p.selectedNodeId
 * @param {string} p.canvasLabelMode
 * @param {import("react").MutableRefObject<Set<string> | null> | null} [p.activeForLabelSetRef]
 */
export function useGraphCanvasInputHoverPick({
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
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [hoveredEdgeId, setHoveredEdgeId] = useState("");
  const [canvasCursor, setCanvasCursor] = useState("grab");

  const hoverPickPendingRef = useRef(false);
  const hoverClientRef = useRef({ x: 0, y: 0 });
  const hoverPickRafIdRef = useRef(/** @type {number | null} */ (null));

  // Avoid post-unmount RAF + reset coalescing flag if the canvas unmounts before the scheduled frame.
  useEffect(
    () => () => {
      if (hoverPickRafIdRef.current != null) {
        cancelAnimationFrame(hoverPickRafIdRef.current);
        hoverPickRafIdRef.current = null;
      }
      hoverPickPendingRef.current = false;
    },
    [],
  );

  const queueHoverPick = useCallback(
    (clientX, clientY) => {
      hoverClientRef.current = { x: clientX, y: clientY };
      if (hoverPickPendingRef.current) return;
      hoverPickPendingRef.current = true;
      hoverPickRafIdRef.current = requestAnimationFrame(() => {
        hoverPickRafIdRef.current = null;
        hoverPickPendingRef.current = false;
        const canvas = canvasRef.current;
        if (!canvas) return;
        if (dragRef.current.active && dragRef.current.moved) return;
        if (nodeDragRef.current.active && nodeDragRef.current.moved) return;
        const rect = canvas.getBoundingClientRect();
        const lx = hoverClientRef.current.x - rect.left;
        const ly = hoverClientRef.current.y - rect.top;
        const posMap = getPositionsForFrame();
        const hitOpts = buildNodeHitTestScreenOpts({
          graphColorBy,
          graph,
          searchActive,
          searchMatchSet,
          selectedNodeId,
          hoveredNodeId,
          canvasLabelMode,
          activeForLabelSetRef,
        });
        const nodeId =
          hitTestNodeScreen(lx, ly, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel, hitOpts) || "";
        if (nodeId) {
          setHoveredNodeId((prev) => (prev === nodeId ? prev : nodeId));
          setHoveredEdgeId("");
          setCanvasCursor("pointer");
          return;
        }
        setHoveredNodeId("");
        const edgeId = hitTestClosestEdgeId(lx, ly, graph.edges, posMap, transformRef.current);
        setHoveredEdgeId((prev) => (prev === edgeId ? prev : edgeId));
        setCanvasCursor(edgeId ? "pointer" : "grab");
      });
    },
    [
      activeForLabelSetRef,
      canvasLabelMode,
      canvasRef,
      dragRef,
      getPositionsForFrame,
      graph,
      graphColorBy,
      hoveredNodeId,
      nodeDragRef,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      transformRef,
    ],
  );

  const clearHover = useCallback(() => {
    setHoveredNodeId("");
    setHoveredEdgeId("");
    setCanvasCursor("grab");
  }, []);

  return {
    hoveredNodeId,
    hoveredEdgeId,
    canvasCursor,
    setHoveredNodeId,
    setHoveredEdgeId,
    setCanvasCursor,
    queueHoverPick,
    clearHover,
  };
}
