import { hitTestClosestEdgeId, hitTestNodeScreen } from "../../graphCanvasDraw.js";

import { buildNodeHitTestScreenOpts } from "./hitTestContext.js";

/**
 * Hit-test after a non-drag pan gesture: node, edge, or empty canvas.
 *
 * @param {object} ctx
 * @param {import("react").RefObject<HTMLCanvasElement | null>} ctx.canvasRef
 * @param {() => Map<string, { x: number; y: number }>} ctx.getPositionsForFrame
 * @param {{ nodes: unknown[]; edges: unknown[] }} ctx.graph
 * @param {import("react").MutableRefObject<{ scale: number; tx: number; ty: number }>} ctx.transformRef
 * @param {(node: unknown) => string | null} ctx.resolveNodeCanvasLabel
 * @param {string} ctx.graphColorBy
 * @param {string} ctx.hoveredNodeId
 * @param {boolean} ctx.searchActive
 * @param {unknown} ctx.searchMatchSet
 * @param {string} ctx.selectedNodeId
 * @param {string} ctx.canvasLabelMode
 * @param {import("react").MutableRefObject<Set<string> | null> | null} [ctx.activeForLabelSetRef]
 * @param {number} clientX
 * @param {number} clientY
 * @returns {{ kind: "node"; nodeId: string } | { kind: "edge"; edgeId: string } | { kind: "canvas" }}
 */
export function resolveGraphCanvasClickSelection(ctx, clientX, clientY) {
  const canvas = ctx.canvasRef.current;
  if (!canvas) return { kind: "canvas" };
  const rect = canvas.getBoundingClientRect();
  const x = clientX - rect.left;
  const y = clientY - rect.top;
  const posMap = ctx.getPositionsForFrame();
  const hitOpts = buildNodeHitTestScreenOpts({
    graphColorBy: ctx.graphColorBy,
    graph: ctx.graph,
    searchActive: ctx.searchActive,
    searchMatchSet: ctx.searchMatchSet,
    selectedNodeId: ctx.selectedNodeId,
    hoveredNodeId: ctx.hoveredNodeId,
    canvasLabelMode: ctx.canvasLabelMode,
    activeForLabelSetRef: ctx.activeForLabelSetRef,
  });
  const nodeId = hitTestNodeScreen(x, y, ctx.graph.nodes, posMap, ctx.transformRef.current, ctx.resolveNodeCanvasLabel, hitOpts);
  if (nodeId) return { kind: "node", nodeId };
  const edgeId = hitTestClosestEdgeId(x, y, ctx.graph.edges, posMap, ctx.transformRef.current);
  if (edgeId) return { kind: "edge", edgeId };
  return { kind: "canvas" };
}
