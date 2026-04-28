/**
 * In-place updates to the live force-simulation node array (shared with {@link useScienceGraphForceSimulation}).
 */

/**
 * Set world position and zero velocity on the first node matching `nodeId`.
 *
 * @param {Array<{ id: string, x?: number, y?: number, vx?: number, vy?: number }>} buf
 * @param {string} nodeId
 * @param {number} x
 * @param {number} y
 */
export function writeSimNodeWorldPosition(buf, nodeId, x, y) {
  for (let i = 0; i < buf.length; i++) {
    if (buf[i].id === nodeId) {
      buf[i].x = x;
      buf[i].y = y;
      buf[i].vx = 0;
      buf[i].vy = 0;
      return;
    }
  }
}
