import { MIN_FIT_SCALE } from "./graphCanvasMvpConstants.js";
import { computeFitTransform } from "./graphCanvasTransform.js";

/**
 * Enforce minimum zoom so tiny subgraph fits do not over-zoom past readable scale.
 *
 * @param {{ scale: number, tx: number, ty: number }} fit
 * @returns {{ scale: number, tx: number, ty: number }}
 */
export function clampGraphCanvasFitTransform(fit) {
  return { ...fit, scale: Math.max(fit.scale, MIN_FIT_SCALE) };
}

/**
 * @param {Map<string, { x: number, y: number }>} allPositions
 * @param {Iterable<string>} nodeIds
 * @returns {Map<string, { x: number, y: number }>}
 */
export function buildPositionSubset(allPositions, nodeIds) {
  const out = new Map();
  if (!allPositions || !(allPositions instanceof Map)) return out;
  for (const id of nodeIds) {
    const key = id != null ? String(id).trim() : "";
    if (!key) continue;
    const p = allPositions.get(key);
    if (p) out.set(key, p);
  }
  return out;
}

/**
 * Fit viewport to the bounding box of the given node ids (subset of allPositions).
 *
 * @param {Map<string, { x: number, y: number }>} allPositions
 * @param {Iterable<string>} nodeIds
 * @param {number} viewportW
 * @param {number} viewportH
 * @param {number} nodeRadius
 * @param {number} padding
 * @returns {{ scale: number, tx: number, ty: number } | null}
 */
export function computeFitTransformForNodeSubset(allPositions, nodeIds, viewportW, viewportH, nodeRadius, padding) {
  const subset = buildPositionSubset(allPositions, nodeIds);
  if (subset.size === 0) return null;
  return computeFitTransform(subset, viewportW, viewportH, nodeRadius, padding);
}
