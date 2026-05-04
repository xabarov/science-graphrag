import { drawCommunityHulls } from "./graphCanvasDrawCommunityHulls.js";
import { drawEdges, drawLabels, drawNodes } from "./graphCanvasDraw.js";

/**
 * Single canvas paint pass for {@link GraphCanvasMvp} (clears, hulls, edges, nodes, labels).
 *
 * @param {object} p
 * @param {import("react").RefObject<HTMLCanvasElement | null>} p.canvasRef
 * @param {import("react").RefObject<HTMLElement | null>} p.canvasHostRef
 * @param {() => { w: number, h: number }} p.getViewportDims
 * @param {string} p.canvasBg
 * @param {() => Map<string, { x: number, y: number }>} p.getPositionsForFrame
 * @param {import("react").MutableRefObject<Map<string, { x: number, y: number }>>} p.positionsRef
 * @param {import("react").MutableRefObject<{ scale: number, tx: number, ty: number }>} p.transformRef
 * @param {object} p.graph
 * @param {Map<string, object>} p.nodeById
 * @param {string} p.selectedNodeId
 * @param {string} p.selectedEdgeId
 * @param {string | undefined | null} p.hoveredNodeId
 * @param {string | undefined | null} p.hoveredEdgeId
 * @param {boolean} p.searchActive
 * @param {Set<string>} p.searchMatchSet
 * @param {object} p.drawOptsBase appearance/colorBy/nodeCommunityMap/communityColorStyleMap bucket
 * @param {boolean} p.graphCommunityHulls
 * @param {Map<string, unknown>} p.nodeCommunityMap
 * @param {Map<string, number>} p.communityRanks
 * @param {(rankOneBased: number, nodeCount: number) => string} p.formatHullLabel
 * @param {(e: object) => string} p.resolveEdgeLabel
 * @param {(node: object) => string | null} p.resolveNodeCanvasLabel
 * @param {"all"|"interaction"|"adaptive"} p.canvasLabelMode
 * @param {Set<string>} p.activeForLabelSet
 */
export function paintGraphCanvasMvpFrame({
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
  formatHullLabel,
  resolveEdgeLabel,
  resolveNodeCanvasLabel,
  canvasLabelMode,
  activeForLabelSet,
}) {
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
  const labelActive = activeForLabelSet instanceof Set ? activeForLabelSet : new Set();
  const nodeStyleMap = Object.fromEntries(
    graph.nodes.map((node) => [
      node.id,
      {
        selected: node.id === selectedNodeId,
        hovered: !selectedNodeId && node.id === hoveredNodeId,
        searchDim: searchActive && !searchMatchSet.has(node.id),
        focusDim: Boolean(String(selectedNodeId || "").trim()) && !labelActive.has(node.id),
      },
    ]),
  );
  const edgeStyleMap = Object.fromEntries(
    graph.edges.map((edge) => [edge.id, { active: edge.id === selectedEdgeId || edge.id === hoveredEdgeId }]),
  );
  const drawOpts = { ...drawOptsBase };
  const appearance = drawOptsBase.appearance;
  const graphColorBy = drawOptsBase.colorBy;
  if (graphColorBy === "community" && graphCommunityHulls) {
    drawCommunityHulls(ctx, graph.nodes, positions, transformRef.current, nodeCommunityMap, drawOptsBase.communityColorStyleMap, {
      appearance,
      communityRanks,
      formatHullLabel,
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
}
