import {
  edgeTypeCanvasLabel,
  getScienceGraphNodeStyle,
  truncateCanvasLabel,
} from "./graphCanvasStyle.js";
import { clipSegmentByDiscInsets, distancePointToSegment } from "./graphCanvasGeometry.js";
import { worldToScreen } from "./graphCanvasTransform.js";

const LABEL_FONT =
  '600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
const EDGE_LABEL_FONT =
  '400 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
const NODE_RADIUS = 12;
const ARROW_HEAD_LEN = 7;
const ARROW_HEAD_HW = 4;
const EDGE_HOVER_THRESHOLD_PX = 8;

export function drawEdges(ctx, edges, nodeMap, positions, transform, styleMap = {}) {
  const { scale, tx, ty } = transform;
  for (const edge of edges) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const edgeStyle = styleMap[String(edge.id || "")] || {};
    const edgeActive = Boolean(edgeStyle.active);
    const n0 = nodeMap.get(edge.source);
    const n1 = nodeMap.get(edge.target);
    const extEdge =
      String(n0?.workspaceMembership || "").toLowerCase() === "external" ||
      String(n1?.workspaceMembership || "").toLowerCase() === "external";
    ctx.setLineDash(extEdge ? [5, 4] : []);
    const clipped = clipSegmentByDiscInsets(p0, p1, NODE_RADIUS, NODE_RADIUS);
    ctx.strokeStyle = edgeActive
      ? "rgba(255,255,255,0.38)"
      : extEdge
        ? "rgba(255,255,255,0.08)"
        : "rgba(255,255,255,0.12)";
    ctx.lineWidth = edgeActive ? 1.75 : 1;
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
      ctx.fillStyle = edgeActive ? "rgba(255,255,255,0.38)" : "rgba(255,255,255,0.2)";
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

export function drawNodes(ctx, nodes, positions, transform, styleMap = {}) {
  const { scale, tx, ty } = transform;
  for (const node of nodes) {
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const style = getScienceGraphNodeStyle(node.type, {
      selected: Boolean(styleMap[String(node.id || "")]?.selected),
      hovered: Boolean(styleMap[String(node.id || "")]?.hovered),
      workspaceMembership: node.workspaceMembership,
      nodeKind: node.nodeKind,
    });
    ctx.beginPath();
    ctx.arc(p.x, p.y, NODE_RADIUS, 0, 2 * Math.PI);
    ctx.fillStyle = style.fill;
    ctx.fill();
    ctx.strokeStyle = style.stroke;
    ctx.lineWidth = style.lineWidth;
    if (Array.isArray(style.strokeDash) && style.strokeDash.length > 0) ctx.setLineDash(style.strokeDash);
    ctx.stroke();
    ctx.setLineDash([]);
    if (node.nodeKind === "Aggregator") {
      const badge = node.raw?.aggregation_hints?.count;
      const badgeText = Number.isFinite(Number(badge)) ? `+${Number(badge)}` : "+";
      ctx.font = '700 11px Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "rgba(129, 140, 248, 0.95)";
      ctx.fillText(badgeText, p.x, p.y);
    }
  }
}

export function drawLabels(ctx, nodes, edges, positions, transform, styleMap = {}) {
  const { scale, tx, ty } = transform;
  ctx.font = EDGE_LABEL_FONT;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (const edge of edges) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const elabel = edgeTypeCanvasLabel(edge.type);
    if (!elabel || elabel === "—") continue;
    const midX = (p0.x + p1.x) / 2;
    const midY = (p0.y + p1.y) / 2;
    const metrics = ctx.measureText(elabel);
    const bw = metrics.width + 8;
    const bh = 16;
    const active = Boolean(styleMap[String(edge.id || "")]?.active);
    ctx.fillStyle = active ? "rgba(40, 40, 40, 0.96)" : "rgba(26, 26, 26, 0.94)";
    ctx.fillRect(midX - bw / 2, midY - bh / 2, bw, bh);
    ctx.strokeStyle = active ? "rgba(255, 255, 255, 0.2)" : "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;
    ctx.strokeRect(midX - bw / 2, midY - bh / 2, bw, bh);
    ctx.fillStyle = active ? "rgba(255, 255, 255, 0.82)" : "rgba(255, 255, 255, 0.62)";
    ctx.fillText(elabel, midX, midY);
  }
  ctx.font = LABEL_FONT;
  for (const node of nodes) {
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const sel = Boolean(styleMap[String(node.id || "")]?.selected);
    const rawLabel =
      node.displayLabel != null && String(node.displayLabel).trim()
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
    ctx.fillStyle = "rgba(26, 26, 26, 0.95)";
    ctx.fillRect(p.x - boxW / 2, boxTop, boxW, boxH);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
    ctx.lineWidth = 1;
    ctx.strokeRect(p.x - boxW / 2, boxTop, boxW, boxH);
    ctx.fillStyle = sel ? "rgba(255, 255, 255, 0.92)" : "rgba(255, 255, 255, 0.82)";
    ctx.fillText(text, p.x, midY);
  }
}

export function hitTestNode(worldX, worldY, nodeMap, positions) {
  for (const node of nodeMap.values()) {
    const p = positions.get(node.id);
    if (!p) continue;
    const dx = worldX - p.x;
    const dy = worldY - p.y;
    if (dx * dx + dy * dy <= NODE_RADIUS * NODE_RADIUS) return node.id;
  }
  return null;
}

export function hitTestClosestEdgeId(screenX, screenY, edges, positions, transform) {
  const { scale, tx, ty } = transform;
  let best = "";
  let bestD = EDGE_HOVER_THRESHOLD_PX + 1;
  for (const edge of edges) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const d = distancePointToSegment(screenX, screenY, p0.x, p0.y, p1.x, p1.y);
    if (d < bestD) {
      bestD = d;
      best = edge.id;
    }
  }
  return bestD <= EDGE_HOVER_THRESHOLD_PX ? best : "";
}
