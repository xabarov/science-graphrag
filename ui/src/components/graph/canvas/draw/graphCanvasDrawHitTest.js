import { distancePointToSegment } from "../graphCanvasGeometry.js";
import { truncateCanvasLabel } from "../graphCanvasStyle.js";
import { worldToScreen } from "../graphCanvasTransform.js";
import {
  EDGE_HOVER_THRESHOLD_PX,
  NODE_HIT_RADIUS,
  NODE_LABEL_HIT_PADDING_X,
  NODE_LABEL_HIT_PADDING_Y,
  NODE_RADIUS,
} from "./graphCanvasDrawConstants.js";
import { shouldDrawCanvasNodeLabel } from "./graphCanvasDrawLabelPolicy.js";

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
