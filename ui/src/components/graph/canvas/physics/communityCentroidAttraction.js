/**
 * O(n)-per-tick community attraction toward a per-node centroid (Phase B).
 *
 * Legacy pairwise attraction skipped edges to the currently dragged node. We match that by
 * excluding the dragged node from the centroid used as the attractor for all other cluster members.
 *
 * For node i (not dragged): centroid uses cluster members j where j !== i and j is not the dragged
 * node id. Positions use live (x,y) from the integrator buffer; the dragged member uses
 * draggedPos when included only in the global sum — we subtract it when building the attractor
 * set for others, so dragged coordinates still define the dragged vertex for repulsion/links but
 * do not act as a community pull target (same as legacy skip when the peer is the dragged node).
 *
 * Force law matches legacy scalar: magnitude = dist * strength * cooling, direction toward centroid.
 */

/**
 * @param {Map<unknown, string[]>} communityMap clusterId -> sorted node ids
 * @param {Map<string, { x: number, y: number }>} nodeMap id -> node (mutating sim buffer)
 * @param {{ id: string, x: number, y: number } | null | undefined} draggedPos
 * @returns {Map<unknown, { sumX: number, sumY: number, count: number, draggedMemberId: string | null }>}
 */
export function buildClusterPositionStats(communityMap, nodeMap, draggedPos) {
  /** @type {Map<unknown, { sumX: number, sumY: number, count: number, draggedMemberId: string | null }>} */
  const stats = new Map();
  if (!communityMap || communityMap.size === 0) return stats;

  const draggedId = draggedPos && draggedPos.id != null ? String(draggedPos.id) : null;

  communityMap.forEach((ids, clusterId) => {
    let sumX = 0;
    let sumY = 0;
    let count = 0;
    let draggedMemberId = null;
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const node = nodeMap.get(id);
      if (!node) continue;
      const isDraggedMember = draggedId != null && String(id) === draggedId;
      if (isDraggedMember) draggedMemberId = draggedId;
      const x = isDraggedMember ? draggedPos.x : node.x;
      const y = isDraggedMember ? draggedPos.y : node.y;
      sumX += x;
      sumY += y;
      count += 1;
    }
    stats.set(clusterId, { sumX, sumY, count, draggedMemberId });
  });
  return stats;
}

/**
 * @param {string} nodeId
 * @param {unknown} clusterId
 * @param {Map<unknown, { sumX: number, sumY: number, count: number, draggedMemberId: string | null }>} clusterStats
 * @param {{ x: number, y: number }} nodePos position of the current node (integrator)
 * @param {{ id: string, x: number, y: number } | null | undefined} draggedPos
 * @param {number} strength e.g. CLUSTER_ATTRACTION_STRENGTH
 * @param {number} cooling e.g. cooling temperature in (0,1]
 * @param {(n: number) => number} sqrtFn
 * @returns {{ fx: number, fy: number }}
 */
export function centroidCommunityForce(
  nodeId,
  clusterId,
  clusterStats,
  nodePos,
  draggedPos,
  strength,
  cooling,
  sqrtFn = Math.sqrt,
) {
  const st = clusterStats.get(clusterId);
  if (!st || st.count < 2) return { fx: 0, fy: 0 };

  const draggedId = draggedPos && draggedPos.id != null ? String(draggedPos.id) : null;
  const nid = String(nodeId);

  let sx = st.sumX - nodePos.x;
  let sy = st.sumY - nodePos.y;
  let denom = st.count - 1;

  if (draggedId && st.draggedMemberId === draggedId && draggedId !== nid) {
    sx -= draggedPos.x;
    sy -= draggedPos.y;
    denom -= 1;
  }

  if (denom < 1) return { fx: 0, fy: 0 };

  const cx = sx / denom;
  const cy = sy / denom;
  const dx = cx - nodePos.x;
  const dy = cy - nodePos.y;
  const distSq = dx * dx + dy * dy + 1;
  const dist = sqrtFn(distSq);
  const communityForce = dist * strength * cooling;
  const invDist = 1 / dist;
  return { fx: dx * invDist * communityForce, fy: dy * invDist * communityForce };
}
