import { edgeTypeCanvasLabelFromEdge, truncateCanvasLabel } from "../graphCanvasStyle.js";
import { worldToScreen } from "../graphCanvasTransform.js";
import {
  EDGE_LABEL_FONT,
  LABEL_FONT,
  NODE_RADIUS,
} from "./graphCanvasDrawConstants.js";
import { shouldDrawCanvasEdgeLabel, shouldDrawCanvasNodeLabel } from "./graphCanvasDrawLabelPolicy.js";

/**
 * @typedef {{
 *   resolveEdgeLabel?: (edge: object) => string,
 *   resolveNodeCanvasLabel?: (node: object) => string | null | undefined,
 *   canvasLabelMode?: "all" | "interaction" | "adaptive",
 *   edgeCountForAdaptive?: number,
 *   appearance?: "light" | "dark",
 *   colorBy?: "type" | "community",
 *   nodeCountForAdaptive?: number,
 *   searchActive?: boolean,
 *   searchMatchSet?: Set<string> | null,
 *   activeForLabelSet?: Set<string> | null,
 * }} DrawLabelOptions
 */

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {Iterable<object>} nodes
 * @param {Iterable<object>} edges
 * @param {Map<string, { x: number, y: number }>} positions
 * @param {{ scale: number, tx: number, ty: number }} transform
 * @param {Record<string, { selected?: boolean, hovered?: boolean, active?: boolean }>} styleMap
 * @param {DrawLabelOptions} [drawOptions]
 */
export function drawLabels(ctx, nodes, edges, positions, transform, styleMap = {}, drawOptions = {}) {
  const light = String(drawOptions.appearance || "dark") === "light";
  const edgeBoxActive = light ? "rgba(248,250,252,0.98)" : "rgba(40, 40, 40, 0.96)";
  const edgeBoxIdle = light ? "rgba(255,255,255,0.96)" : "rgba(26, 26, 26, 0.94)";
  const edgeStrokeActive = light ? "rgba(15,23,42,0.22)" : "rgba(255, 255, 255, 0.2)";
  const edgeStrokeIdle = light ? "rgba(15,23,42,0.12)" : "rgba(255, 255, 255, 0.08)";
  const edgeTextActive = light ? "rgba(15,23,42,0.88)" : "rgba(255, 255, 255, 0.82)";
  const edgeTextIdle = light ? "rgba(15,23,42,0.62)" : "rgba(255, 255, 255, 0.62)";
  const nodeBoxFill = light ? "rgba(255,255,255,0.96)" : "rgba(26, 26, 26, 0.95)";
  const nodeBoxStroke = light ? "rgba(15,23,42,0.12)" : "rgba(255, 255, 255, 0.08)";
  const nodeTextSel = light ? "rgba(15,23,42,0.92)" : "rgba(255, 255, 255, 0.92)";
  const nodeTextIdle = light ? "rgba(15,23,42,0.82)" : "rgba(255, 255, 255, 0.82)";
  const { scale, tx, ty } = transform;
  const resolveEdge = typeof drawOptions.resolveEdgeLabel === "function" ? drawOptions.resolveEdgeLabel : null;
  const resolveNode = typeof drawOptions.resolveNodeCanvasLabel === "function" ? drawOptions.resolveNodeCanvasLabel : null;
  const canvasLabelMode =
    drawOptions.canvasLabelMode === "interaction" || drawOptions.canvasLabelMode === "adaptive"
      ? drawOptions.canvasLabelMode
      : "all";
  const edgeList = Array.isArray(edges) ? edges : [...edges];
  const edgeCountForAdaptive =
    typeof drawOptions.edgeCountForAdaptive === "number" && Number.isFinite(drawOptions.edgeCountForAdaptive)
      ? drawOptions.edgeCountForAdaptive
      : edgeList.length;
  const colorBy = drawOptions.colorBy === "community" ? "community" : "type";
  const nodeCountForAdaptive =
    typeof drawOptions.nodeCountForAdaptive === "number" && Number.isFinite(drawOptions.nodeCountForAdaptive)
      ? drawOptions.nodeCountForAdaptive
      : Array.isArray(nodes)
        ? nodes.length
        : [...nodes].length;
  const searchActive = Boolean(drawOptions.searchActive);
  const searchMatchSet = drawOptions.searchMatchSet instanceof Set ? drawOptions.searchMatchSet : null;
  const activeForLabelSet =
    drawOptions.activeForLabelSet instanceof Set ? drawOptions.activeForLabelSet : null;
  ctx.font = EDGE_LABEL_FONT;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (const edge of edgeList) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const edgeId = String(edge.id || "");
    const baseStyle = styleMap[edgeId] || {};
    // Treat an edge connecting two label-active nodes (e.g. selected node + 1-hop neighbor) as
    // active-for-label so the relationship label shows alongside the highlighted endpoints.
    const neighborActive =
      activeForLabelSet
        ? activeForLabelSet.has(String(edge.source)) && activeForLabelSet.has(String(edge.target))
        : false;
    const edgeStyleForLabel = neighborActive ? { ...baseStyle, active: true } : baseStyle;
    if (!shouldDrawCanvasEdgeLabel(canvasLabelMode, edgeStyleForLabel, transform, edgeCountForAdaptive)) {
      continue;
    }
    const elabel = resolveEdge ? resolveEdge(edge) : edgeTypeCanvasLabelFromEdge(edge);
    if (!elabel || elabel === "—") continue;
    const midX = (p0.x + p1.x) / 2;
    const midY = (p0.y + p1.y) / 2;
    const metrics = ctx.measureText(elabel);
    const bw = metrics.width + 8;
    const bh = 16;
    const active = Boolean(baseStyle.active);
    ctx.fillStyle = active ? edgeBoxActive : edgeBoxIdle;
    ctx.fillRect(midX - bw / 2, midY - bh / 2, bw, bh);
    ctx.strokeStyle = active ? edgeStrokeActive : edgeStrokeIdle;
    ctx.lineWidth = 1;
    ctx.strokeRect(midX - bw / 2, midY - bh / 2, bw, bh);
    ctx.fillStyle = active ? edgeTextActive : edgeTextIdle;
    ctx.fillText(elabel, midX, midY);
  }
  ctx.font = LABEL_FONT;
  for (const node of nodes) {
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const sid = String(node.id || "");
    const sm = styleMap[sid] || {};
    const sel = Boolean(sm.selected);
    if (
      !shouldDrawCanvasNodeLabel({
        colorBy,
        transform,
        nodeCount: nodeCountForAdaptive,
        searchActive,
        searchMatchSet,
        nodeId: sid,
        styleEntry: sm,
        mode: canvasLabelMode,
        activeForLabelSet,
      })
    ) {
      continue;
    }
    const resolvedNode = resolveNode ? resolveNode(node) : null;
    const rawLabel =
      resolvedNode != null && String(resolvedNode).trim()
        ? String(resolvedNode)
        : node.displayLabel != null && String(node.displayLabel).trim()
          ? node.displayLabel
          : node.label != null && String(node.label).trim()
            ? node.label
            : node.id;
    const text = truncateCanvasLabel(rawLabel);
    const metrics = ctx.measureText(text);
    const boxW = metrics.width + 12;
    const boxH = 20;
    const boxTop = p.y + NODE_RADIUS + 4;
    const midY = boxTop + boxH / 2;
    ctx.fillStyle = nodeBoxFill;
    ctx.fillRect(p.x - boxW / 2, boxTop, boxW, boxH);
    ctx.strokeStyle = nodeBoxStroke;
    ctx.lineWidth = 1;
    ctx.strokeRect(p.x - boxW / 2, boxTop, boxW, boxH);
    ctx.fillStyle = sel ? nodeTextSel : nodeTextIdle;
    ctx.fillText(text, p.x, midY);
  }
}
