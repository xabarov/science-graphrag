/**
 * World/screen transform helpers for GraphCanvasMvp (unit-tested, Phase 4.4).
 */

export const DEFAULT_WORLD_RADIUS = 200;

/** Up to this many nodes keep {@link DEFAULT_WORLD_RADIUS}; above that the ring grows (~√n). */
export const WORLD_RADIUS_GROWTH_START = 10;

const WORLD_RADIUS_GROWTH_K = 12;
/** Upper cap so very large capped UI graphs stay bounded in world space. */
export const MAX_WORLD_RADIUS = 520;
/** Lower cap after growth formula (should not go below this once growth applies). */
export const MIN_WORLD_RADIUS = 160;

/**
 * Deterministic circle radius in world units so dense neighborhoods get a larger ring before fit-scale shrinks them.
 *
 * @param {number} n
 * @returns {number}
 */
export function worldRadiusForNodeCount(n) {
  const count = Math.max(0, Math.floor(Number(n)));
  if (count <= WORLD_RADIUS_GROWTH_START) {
    return DEFAULT_WORLD_RADIUS;
  }
  const extra = WORLD_RADIUS_GROWTH_K * Math.sqrt(count - WORLD_RADIUS_GROWTH_START);
  return Math.min(MAX_WORLD_RADIUS, Math.max(MIN_WORLD_RADIUS, DEFAULT_WORLD_RADIUS + extra));
}

/**
 * @param {Array<{ id: string }>} nodes
 * @param {number} worldRadius
 * @returns {Map<string, { x: number, y: number }>}
 */
export function computeWorldLayout(nodes, worldRadius = DEFAULT_WORLD_RADIUS) {
  const positions = new Map();
  const n = nodes.length;
  if (n === 0) return positions;
  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    positions.set(node.id, {
      x: worldRadius * Math.cos(angle),
      y: worldRadius * Math.sin(angle),
    });
  });
  return positions;
}

/**
 * @param {Map<string, { x: number, y: number }>} positions
 * @param {number} w
 * @param {number} h
 * @param {number} nodeR
 * @param {number} padding
 * @returns {{ scale: number, tx: number, ty: number }}
 */
export function computeFitTransform(positions, w, h, nodeR, padding) {
  if (positions.size === 0) {
    return { scale: 1, tx: w / 2, ty: h / 2 };
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of positions.values()) {
    minX = Math.min(minX, p.x - nodeR);
    minY = Math.min(minY, p.y - nodeR);
    maxX = Math.max(maxX, p.x + nodeR);
    maxY = Math.max(maxY, p.y + nodeR);
  }
  const bw = Math.max(maxX - minX, 1);
  const bh = Math.max(maxY - minY, 1);
  const innerW = Math.max(1, w - 2 * padding);
  const innerH = Math.max(1, h - 2 * padding);
  const scale = Math.min(innerW / bw, innerH / bh) * 0.92;
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return {
    scale,
    tx: w / 2 - cx * scale,
    ty: h / 2 - cy * scale,
  };
}

/**
 * @param {number} sx
 * @param {number} sy
 * @param {number} scale
 * @param {number} tx
 * @param {number} ty
 */
export function screenToWorld(sx, sy, scale, tx, ty) {
  return { x: (sx - tx) / scale, y: (sy - ty) / scale };
}

/**
 * @param {number} wx
 * @param {number} wy
 * @param {number} scale
 * @param {number} tx
 * @param {number} ty
 */
export function worldToScreen(wx, wy, scale, tx, ty) {
  return { x: wx * scale + tx, y: wy * scale + ty };
}
