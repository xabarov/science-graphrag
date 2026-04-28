/**
 * Legend rows and preview labels for UI communities (Wave GR-COM-1).
 */

import { sortedCommunitiesByCount } from "../canvas/physics/communityPalette.js";

/**
 * @param {{ nodes?: Array<{ id: string }>, edges?: Array<{ source: string, target: string }> }} graph
 * @returns {Map<string, number>}
 */
export function nodeDegreeMap(graph) {
  const deg = new Map();
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  nodes.forEach((n) => {
    if (n?.id != null) deg.set(String(n.id), 0);
  });
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  edges.forEach((e) => {
    const s = e?.source != null ? String(e.source) : "";
    const t = e?.target != null ? String(e.target) : "";
    if (deg.has(s)) deg.set(s, (deg.get(s) || 0) + 1);
    if (deg.has(t)) deg.set(t, (deg.get(t) || 0) + 1);
  });
  return deg;
}

/**
 * @param {object} node
 * @returns {string}
 */
export function communityPreviewLabelForNode(node) {
  if (!node) return "—";
  if (node.displayLabel != null && String(node.displayLabel).trim()) return String(node.displayLabel).trim();
  if (node.label != null && String(node.label).trim()) return String(node.label).trim();
  if (node.title != null && String(node.title).trim()) return String(node.title).trim();
  if (node.id != null) return String(node.id);
  return "—";
}

/**
 * @param {{ nodes?: object[], edges?: object[] }} graph
 * @param {Map<string, string>} nodeCommunityMap
 * @param {{ topN?: number, previewsPerCommunity?: number }} [opts]
 * @returns {Array<{ communityId: string, count: number, previews: string[], rankOneBased: number }>}
 * Rank order matches {@link sortedCommunitiesByCount} and hull label numbering on canvas.
 */
export function buildCommunityLegendRows(graph, nodeCommunityMap, opts = {}) {
  const topN = typeof opts.topN === "number" && opts.topN > 0 ? opts.topN : 12;
  const previewsPerCommunity =
    typeof opts.previewsPerCommunity === "number" && opts.previewsPerCommunity > 0 ? opts.previewsPerCommunity : 3;

  const rankByCommunityId = new Map();
  sortedCommunitiesByCount(nodeCommunityMap).forEach((row, idx) => {
    rankByCommunityId.set(String(row.id), idx + 1);
  });

  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const byCommunity = new Map();
  nodeCommunityMap.forEach((cid, nid) => {
    const id = String(cid);
    if (!byCommunity.has(id)) byCommunity.set(id, []);
    byCommunity.get(id).push(String(nid));
  });

  const deg = nodeDegreeMap(graph);
  const nodeById = new Map(nodes.map((n) => [String(n.id), n]));

  const rows = [...byCommunity.entries()]
    .map(([communityId, ids]) => ({ communityId, count: ids.length, ids }))
    .sort((a, b) => b.count - a.count || String(a.communityId).localeCompare(String(b.communityId)));

  return rows.slice(0, topN).map((row) => {
    const sortedIds = [...row.ids].sort((a, b) => {
      const da = deg.get(a) || 0;
      const db = deg.get(b) || 0;
      if (db !== da) return db - da;
      return a.localeCompare(b);
    });
    const previews = sortedIds.slice(0, previewsPerCommunity).map((id) => communityPreviewLabelForNode(nodeById.get(id)));
    const rankOneBased = rankByCommunityId.get(String(row.communityId)) ?? 0;
    return { communityId: row.communityId, count: row.count, previews, rankOneBased };
  });
}
