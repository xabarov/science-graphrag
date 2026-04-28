/**
 * Pure geometry helpers for graph canvas (screen-space).
 */

/**
 * Shortest distance from point P to segment AB.
 * @param {number} px
 * @param {number} py
 * @param {number} ax
 * @param {number} ay
 * @param {number} bx
 * @param {number} by
 * @returns {number}
 */
export function distancePointToSegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax;
  const dy = by - ay;
  const len2 = dx * dx + dy * dy;
  if (len2 < 1e-12) {
    const ex = px - ax;
    const ey = py - ay;
    return Math.hypot(ex, ey);
  }
  let t = ((px - ax) * dx + (py - ay) * dy) / len2;
  t = Math.max(0, Math.min(1, t));
  const qx = ax + t * dx;
  const qy = ay + t * dy;
  return Math.hypot(px - qx, py - qy);
}

/**
 * Clip segment between disc centers A and B to the arc endpoints (screen-space radii).
 * Returns null when discs overlap or the segment degenerates.
 * @param {{ x: number, y: number }} a
 * @param {{ x: number, y: number }} b
 * @param {number} radiusAtA
 * @param {number} radiusAtB
 * @returns {{ ax: number, ay: number, bx: number, by: number, ux: number, uy: number } | null}
 */
export function clipSegmentByDiscInsets(a, b, radiusAtA, radiusAtB) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  if (len < 1e-6) return null;
  if (len < radiusAtA + radiusAtB - 1e-3) return null;
  const ux = dx / len;
  const uy = dy / len;
  return {
    ax: a.x + ux * radiusAtA,
    ay: a.y + uy * radiusAtA,
    bx: b.x - ux * radiusAtB,
    by: b.y - uy * radiusAtB,
    ux,
    uy,
  };
}
