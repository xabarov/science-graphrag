import { useCallback, useState } from "react";

import { hitTestNodeScreen } from "../draw/graphCanvasDrawHitTest.js";

/**
 * Context menu state + hit-test open handler for graph canvas MVP.
 *
 * @param {{
 *   canvasRef: import("react").RefObject<HTMLCanvasElement | null>,
 *   graph: { nodes: unknown[], edges: unknown[] },
 *   getPositionsForFrame: () => Map<string, { x: number, y: number }>,
 *   transformRef: import("react").MutableRefObject<{ scale: number, tx: number, ty: number }>,
 *   resolveNodeCanvasLabel: (node: unknown) => string | null,
 *   graphColorBy: string,
 *   searchActive: boolean,
 *   searchMatchSet: Set<string>,
 *   selectedNodeId: string,
 *   hoveredNodeId: string | null | undefined,
 *   canvasLabelMode: string,
 *   activeForLabelSet: Set<string>,
 * }} params
 */
export function useGraphCanvasNodeContextMenu({
  canvasRef,
  graph,
  getPositionsForFrame,
  transformRef,
  resolveNodeCanvasLabel,
  graphColorBy,
  searchActive,
  searchMatchSet,
  selectedNodeId,
  hoveredNodeId,
  canvasLabelMode,
  activeForLabelSet,
}) {
  const [contextMenu, setContextMenu] = useState(
    /** @type {null | { mouseX: number, mouseY: number, nodeId: string }} */ (null),
  );

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
          hoveredNodeId,
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
      hoveredNodeId,
      transformRef,
      canvasRef,
    ],
  );

  const closeContextMenu = useCallback(() => setContextMenu(null), []);

  return { contextMenu, handleCanvasContextMenu, closeContextMenu };
}
