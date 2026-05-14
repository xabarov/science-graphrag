import { clipSegmentByDiscInsets } from "../graphCanvasGeometry.js";
import { worldToScreen } from "../graphCanvasTransform.js";
import { ARROW_HEAD_HW, ARROW_HEAD_LEN, NODE_RADIUS } from "./graphCanvasDrawConstants.js";

/**
 * @param {CanvasRenderingContext2D} ctx
 * @param {object[]} edges
 * @param {Map<string, object>} nodeMap
 * @param {Map<string, { x: number, y: number }>} positions
 * @param {{ scale: number, tx: number, ty: number }} transform
 * @param {Record<string, { active?: boolean }>} [styleMap]
 * @param {{ appearance?: "light" | "dark" }} [drawOpts]
 */
export function drawEdges(ctx, edges, nodeMap, positions, transform, styleMap = {}, drawOpts = {}) {
  const light = String(drawOpts.appearance || "dark") === "light";
  const edgeActive = light ? "rgba(15,23,42,0.42)" : "rgba(255,255,255,0.38)";
  const edgeExt = light ? "rgba(15,23,42,0.12)" : "rgba(255,255,255,0.08)";
  const edgeNorm = light ? "rgba(15,23,42,0.2)" : "rgba(255,255,255,0.12)";
  const arrowFill = light ? "rgba(15,23,42,0.32)" : "rgba(255,255,255,0.2)";
  const { scale, tx, ty } = transform;
  for (const edge of edges) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const edgeStyle = styleMap[String(edge.id || "")] || {};
    const edgeActiveBool = Boolean(edgeStyle.active);
    const n0 = nodeMap.get(edge.source);
    const n1 = nodeMap.get(edge.target);
    const extEdge =
      String(n0?.workspaceMembership || "").toLowerCase() === "external" ||
      String(n1?.workspaceMembership || "").toLowerCase() === "external";
    ctx.setLineDash(extEdge ? [5, 4] : []);
    const clipped = clipSegmentByDiscInsets(p0, p1, NODE_RADIUS, NODE_RADIUS);
    ctx.strokeStyle = edgeActiveBool ? edgeActive : extEdge ? edgeExt : edgeNorm;
    ctx.lineWidth = edgeActiveBool ? 1.75 : 1;
    if (clipped) {
      const { ax, ay, bx, by, ux, uy } = clipped;
      const lineEndX = bx - ux * ARROW_HEAD_LEN;
      const lineEndY = by - uy * ARROW_HEAD_LEN;
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(lineEndX, lineEndY);
      ctx.stroke();
      const px = -uy;
      const py = ux;
      ctx.beginPath();
      ctx.moveTo(bx, by);
      ctx.lineTo(lineEndX + px * ARROW_HEAD_HW, lineEndY + py * ARROW_HEAD_HW);
      ctx.lineTo(lineEndX - px * ARROW_HEAD_HW, lineEndY - py * ARROW_HEAD_HW);
      ctx.closePath();
      ctx.fillStyle = edgeActiveBool ? edgeActive : arrowFill;
      ctx.fill();
    } else {
      ctx.beginPath();
      ctx.moveTo(p0.x, p0.y);
      ctx.lineTo(p1.x, p1.y);
      ctx.stroke();
    }
  }
  ctx.setLineDash([]);
}
