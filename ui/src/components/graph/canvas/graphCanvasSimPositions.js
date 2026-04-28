/**
 * Build a world-coordinate map from the live force-simulation node buffer (O(n)).
 * Used for canvas drawing and hit-testing while the integrator mutates the buffer in place.
 *
 * @param {Array<{ id: string, x: number, y: number }>} simNodes
 * @returns {Map<string, { x: number, y: number }>}
 */
export function buildWorldPositionsMapFromSimNodes(simNodes) {
  const m = new Map();
  for (let i = 0; i < simNodes.length; i++) {
    const n = simNodes[i];
    m.set(n.id, { x: n.x, y: n.y });
  }
  return m;
}
