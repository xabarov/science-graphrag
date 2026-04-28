/**
 * Deterministic colors for UI communities on the graph canvas (rank-based palette).
 */

export const COMMUNITY_PALETTE_RANK_SLOTS = 16;

/**
 * @param {number} rank 0-based rank among communities sorted by (-count, id)
 * @param {"light" | "dark"} appearance
 * @returns {{ fill: string, stroke: string, hullFill: string, hullStroke: string }}
 */
export function rankedCommunityPalette(rank, appearance) {
  const light = appearance === "light";
  if (rank < 0 || rank >= COMMUNITY_PALETTE_RANK_SLOTS) {
    return neutralCommunityColors(appearance);
  }
  const hue = (rank * 360) / COMMUNITY_PALETTE_RANK_SLOTS;
  if (light) {
    const fill = `hsla(${hue}, 62%, 42%, 0.88)`;
    const stroke = `hsla(${hue}, 55%, 28%, 0.55)`;
    return {
      fill,
      stroke,
      hullFill: `hsla(${hue}, 55%, 45%, 0.07)`,
      hullStroke: `hsla(${hue}, 50%, 35%, 0.22)`,
    };
  }
  const fill = `hsla(${hue}, 58%, 58%, 0.9)`;
  const stroke = `hsla(${hue}, 45%, 78%, 0.45)`;
  return {
    fill,
    stroke,
    hullFill: `hsla(${hue}, 45%, 55%, 0.06)`,
    hullStroke: `hsla(${hue}, 40%, 70%, 0.25)`,
  };
}

/**
 * @param {"light" | "dark"} appearance
 * @returns {{ fill: string, stroke: string, hullFill: string, hullStroke: string }}
 */
export function neutralCommunityColors(appearance) {
  const light = appearance === "light";
  if (light) {
    return {
      fill: "rgba(71, 85, 105, 0.55)",
      stroke: "rgba(51, 65, 85, 0.4)",
      hullFill: "rgba(71, 85, 105, 0.06)",
      hullStroke: "rgba(51, 65, 85, 0.18)",
    };
  }
  return {
    fill: "rgba(148, 163, 184, 0.55)",
    stroke: "rgba(203, 213, 225, 0.35)",
    hullFill: "rgba(148, 163, 184, 0.06)",
    hullStroke: "rgba(203, 213, 225, 0.22)",
  };
}

/**
 * @param {Map<string, string>} nodeCommunityMap nodeId -> communityId
 * @returns {Array<{ id: string, count: number }>}
 */
export function sortedCommunitiesByCount(nodeCommunityMap) {
  const counts = new Map();
  nodeCommunityMap.forEach((cid) => {
    const id = String(cid);
    counts.set(id, (counts.get(id) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => b.count - a.count || String(a.id).localeCompare(String(b.id)));
}

/**
 * @param {Map<string, string>} nodeCommunityMap
 * @param {"light" | "dark"} appearance
 * @returns {Map<string, { fill: string, stroke: string, hullFill: string, hullStroke: string, rank: number }>}
 */
export function buildCommunityColorStyleMap(nodeCommunityMap, appearance) {
  const sorted = sortedCommunitiesByCount(nodeCommunityMap);
  const out = new Map();
  sorted.forEach((row, idx) => {
    const pal = rankedCommunityPalette(idx, appearance);
    out.set(row.id, { ...pal, rank: idx });
  });
  return out;
}
