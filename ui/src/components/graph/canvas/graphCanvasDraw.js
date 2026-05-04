import {
  edgeTypeCanvasLabelFromEdge,
  getScienceGraphNodeStyle,
  truncateCanvasLabel,
} from "./graphCanvasStyle.js";
import { clipSegmentByDiscInsets, distancePointToSegment } from "./graphCanvasGeometry.js";
import { worldToScreen } from "./graphCanvasTransform.js";

/**
 * @param {string} stroke
 * @returns {string}
 */
export function strokeAtHalfAlpha(stroke) {
  const m = String(stroke).match(/rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)/i);
  if (m) {
    const a = Math.min(1, (parseFloat(m[4]) || 0.5) * 0.5);
    return `rgba(${m[1]}, ${m[2]}, ${m[3]}, ${a})`;
  }
  const m2 = String(stroke).match(/rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i);
  if (m2) return `rgba(${m2[1]}, ${m2[2]}, ${m2[3]}, 0.5)`;
  return stroke;
}

const LABEL_FONT =
  '600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
const EDGE_LABEL_FONT =
  '400 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
const NODE_RADIUS = 12;
const NODE_HIT_RADIUS = 18;
const ARROW_HEAD_LEN = 7;
const ARROW_HEAD_HW = 4;
const EDGE_HOVER_THRESHOLD_PX = 8;
const NODE_LABEL_HIT_PADDING_X = 10;
const NODE_LABEL_HIT_PADDING_Y = 8;

/**
 * When edge count exceeds this or scale is below {@link EDGE_LABEL_ADAPTIVE_MIN_SCALE},
 * adaptive mode shows edge labels only for hover/selected edges. Values are tunable.
 */
export const EDGE_LABEL_ADAPTIVE_MAX_EDGES = 72;

/**
 * Above this edge count, adaptive mode behaves like "interaction" for mid-edge labels (paint cost).
 */
export const EDGE_LABEL_MEGA_DENSE_MIN_EDGES = 4000;

/** Below this screen scale (1 = 1px per world unit before pan), adaptive mode treats the view as zoomed out. */
export const EDGE_LABEL_ADAPTIVE_MIN_SCALE = 0.32;

/** When node count exceeds this or scale is below {@link NODE_LABEL_ADAPTIVE_MIN_SCALE}, community-mode node labels are gated. */
export const NODE_LABEL_ADAPTIVE_MAX_NODES = 48;

/** Below this scale, community-mode hides most node labels (selected/hovered/search hits still show). */
export const NODE_LABEL_ADAPTIVE_MIN_SCALE = 0.36;

/**
 * Unified policy for whether to paint a node's canvas label box.
 * The same three-mode contract as edges: "all" shows every label, "interaction" shows only the
 * active-for-label set (selected, hovered, optional 1-hop neighbors), and "adaptive" shows every
 * label when zoom is at or above {@link NODE_LABEL_ADAPTIVE_MIN_SCALE}, otherwise behaves like
 * "interaction" (zoomed-out overview). Search overrides every mode: only matched nodes' labels appear,
 * with hovered/selected still highlighted in interaction.
 *
 * @param {{
 *   colorBy?: "type" | "community",
 *   transform?: { scale?: number },
 *   nodeCount?: number,
 *   searchActive?: boolean,
 *   searchMatchSet?: Set<string> | null,
 *   nodeId?: string,
 *   styleEntry?: { selected?: boolean, hovered?: boolean, searchDim?: boolean },
 *   mode?: "all" | "interaction" | "adaptive",
 *   activeForLabelSet?: Set<string> | null,
 * }} opts
 * @returns {boolean}
 */
export function shouldDrawCanvasNodeLabel(opts) {
  const id = String(opts.nodeId ?? "");
  const sm = opts.styleEntry || {};
  const mode = opts.mode === "interaction" || opts.mode === "adaptive" ? opts.mode : "all";
  const activeSet = opts.activeForLabelSet instanceof Set ? opts.activeForLabelSet : null;
  const searchActive = Boolean(opts.searchActive);
  const searchSet = opts.searchMatchSet instanceof Set ? opts.searchMatchSet : null;
  const isActiveForLabel = Boolean(sm.selected || sm.hovered || (activeSet && activeSet.has(id)));

  if (searchActive) {
    const inSearch = searchSet ? searchSet.has(id) : false;
    if (sm.searchDim || !inSearch) return false;
    if (mode === "interaction") return isActiveForLabel;
    return true;
  }

  if (mode === "all") return true;
  if (mode === "interaction") return isActiveForLabel;

  const scale = opts.transform && Number.isFinite(Number(opts.transform.scale)) ? Number(opts.transform.scale) : 1;
  // "Adaptive" for node labels: use **zoom (scale) only** to decide between "all" vs
  // "interaction-like". If we also OR in `nodeCount > NODE_LABEL_ADAPTIVE_MAX_NODES`, then any
  // graph with 57+ nodes stays interaction-only at every zoom level and strong zoom-in never
  // reveals labels — which contradicts the product expectation for Auto.
  // When zoomed out (scale below threshold), the canvas is visually dense; gate to active only.
  // When zoomed in (scale at/above threshold), show every node label; off-screen labels are
  // clipped by the canvas anyway.
  const zoomedOut = scale < NODE_LABEL_ADAPTIVE_MIN_SCALE;
  if (zoomedOut) return isActiveForLabel;
  return true;
}

/**
 * Whether to paint an edge's mid-label on canvas (node labels are unaffected).
 *
 * @param {"all" | "interaction" | "adaptive"} mode
 * @param {{ active?: boolean }} edgeStyle merged style for the edge id
 * @param {{ scale: number }} transform current pan/zoom
 * @param {number} edgeCount total edges in the current graph (for adaptive density)
 * @returns {boolean}
 */
export function shouldDrawCanvasEdgeLabel(mode, edgeStyle, transform, edgeCount) {
  const active = Boolean(edgeStyle?.active);
  if (mode === "all") return true;
  if (mode === "interaction") return active;
  const nEdges = Number(edgeCount);
  if (nEdges >= EDGE_LABEL_MEGA_DENSE_MIN_EDGES) return active;
  const dense =
    nEdges > EDGE_LABEL_ADAPTIVE_MAX_EDGES || (transform && Number(transform.scale) < EDGE_LABEL_ADAPTIVE_MIN_SCALE);
  if (dense) return active;
  return true;
}

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

export function drawNodes(ctx, nodes, positions, transform, styleMap = {}, drawOpts = {}) {
  const appearance = String(drawOpts.appearance || "dark") === "light" ? "light" : "dark";
  const colorBy = drawOpts.colorBy === "community" ? "community" : "type";
  const nodeCommunityMap = drawOpts.nodeCommunityMap instanceof Map ? drawOpts.nodeCommunityMap : null;
  const communityColorStyleMap =
    drawOpts.communityColorStyleMap instanceof Map ? drawOpts.communityColorStyleMap : null;
  const { scale, tx, ty } = transform;
  for (const node of nodes) {
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const sid = String(node.id || "");
    const sm = styleMap[sid] || {};
    const style = getScienceGraphNodeStyle(node.type, {
      selected: Boolean(sm.selected),
      hovered: Boolean(sm.hovered),
      workspaceMembership: node.workspaceMembership,
      nodeKind: node.nodeKind,
      searchDim: Boolean(sm.searchDim),
      focusDim: Boolean(sm.focusDim),
      appearance,
    });
    let fillStyle = style.fill;
    let strokeStyle = style.stroke;
    const skipCommunityFill = Boolean(sm.selected || sm.hovered || sm.searchDim || sm.focusDim);
    if (colorBy === "community" && nodeCommunityMap && communityColorStyleMap && !skipCommunityFill) {
      const cid = nodeCommunityMap.get(sid);
      if (cid != null) {
        const cs = communityColorStyleMap.get(String(cid));
        if (cs?.fill) fillStyle = cs.fill;
        strokeStyle = strokeAtHalfAlpha(style.stroke);
      }
    }
    ctx.beginPath();
    ctx.arc(p.x, p.y, NODE_RADIUS, 0, 2 * Math.PI);
    ctx.fillStyle = fillStyle;
    ctx.fill();
    ctx.strokeStyle = strokeStyle;
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
      : (Array.isArray(nodes) ? nodes.length : [...nodes].length);
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

/**
 * Pick topmost node at canvas CSS pixel (lx, ly): node disc + label box (matches drawNodes/drawLabels).
 *
 * The label hit target is gated by the same {@link shouldDrawCanvasNodeLabel} policy used by
 * {@link drawLabels} so that pointer hits cannot land on phantom hitboxes for labels that the
 * renderer never drew (e.g. interaction mode without hover/selection/neighbors).
 *
 * @param {number} lx
 * @param {number} ly
 * @param {Iterable<object>} nodes
 * @param {Map<string, { x: number, y: number }>} positions
 * @param {{ scale: number, tx: number, ty: number }} transform
 * @param {(node: object) => string | null | undefined} [resolveNodeLabel]
 * @param {{
 *   colorBy?: "type" | "community",
 *   nodeCount?: number,
 *   searchActive?: boolean,
 *   searchMatchSet?: Set<string> | null,
 *   selectedNodeId?: string,
 *   hoveredNodeId?: string,
 *   mode?: "all" | "interaction" | "adaptive",
 *   activeForLabelSet?: Set<string> | null,
 * }} [nodeLabelHitOpts]
 * @returns {string} node id or ""
 */
export function hitTestNodeScreen(lx, ly, nodes, positions, transform, resolveNodeLabel, nodeLabelHitOpts = {}) {
  const { scale, tx, ty } = transform;
  const list = Array.isArray(nodes) ? [...nodes] : [...nodes];
  const resolveNode = typeof resolveNodeLabel === "function" ? resolveNodeLabel : null;
  const colorBy = nodeLabelHitOpts.colorBy === "community" ? "community" : "type";
  const nodeCount =
    typeof nodeLabelHitOpts.nodeCount === "number" && Number.isFinite(nodeLabelHitOpts.nodeCount)
      ? nodeLabelHitOpts.nodeCount
      : list.length;
  const searchActive = Boolean(nodeLabelHitOpts.searchActive);
  const searchMatchSet = nodeLabelHitOpts.searchMatchSet instanceof Set ? nodeLabelHitOpts.searchMatchSet : null;
  const selectedNodeId = nodeLabelHitOpts.selectedNodeId != null ? String(nodeLabelHitOpts.selectedNodeId) : "";
  const hoveredNodeId = nodeLabelHitOpts.hoveredNodeId != null ? String(nodeLabelHitOpts.hoveredNodeId) : "";
  const mode =
    nodeLabelHitOpts.mode === "interaction" || nodeLabelHitOpts.mode === "adaptive"
      ? nodeLabelHitOpts.mode
      : "all";
  const activeForLabelSet =
    nodeLabelHitOpts.activeForLabelSet instanceof Set ? nodeLabelHitOpts.activeForLabelSet : null;
  for (let i = list.length - 1; i >= 0; i -= 1) {
    const node = list[i];
    const pw = positions.get(node.id);
    if (!pw) continue;
    const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
    const cdx = lx - p.x;
    const cdy = ly - p.y;
    if (cdx * cdx + cdy * cdy <= NODE_HIT_RADIUS * NODE_HIT_RADIUS) return String(node.id);
    const sid = String(node.id || "");
    const styleEntry = {
      selected: sid === selectedNodeId,
      hovered: !selectedNodeId && sid === hoveredNodeId,
      searchDim: searchActive && searchMatchSet && !searchMatchSet.has(sid),
    };
    if (
      !shouldDrawCanvasNodeLabel({
        colorBy,
        transform,
        nodeCount,
        searchActive,
        searchMatchSet,
        nodeId: sid,
        styleEntry,
        mode,
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
    const estChar = 6.2;
    const boxW = Math.min(240, Math.max(36, text.length * estChar + 12));
    const boxH = 20;
    const boxTop = p.y + NODE_RADIUS + 4;
    const boxLeft = p.x - boxW / 2;
    if (
      lx >= boxLeft - NODE_LABEL_HIT_PADDING_X &&
      lx <= boxLeft + boxW + NODE_LABEL_HIT_PADDING_X &&
      ly >= boxTop - NODE_LABEL_HIT_PADDING_Y &&
      ly <= boxTop + boxH + NODE_LABEL_HIT_PADDING_Y
    ) {
      return String(node.id);
    }
  }
  return "";
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
