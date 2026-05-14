/**
 * Per-simulation-run adjacency maps derived from nodes, links, and optional community assignment.
 *
 * @param {import("../../components/graph/model/graphSimulationAdapter.js").SimNode[]} nodes
 * @param {import("../../components/graph/model/graphSimulationAdapter.js").SimLink[]} links
 * @param {Map<string, string> | null} communitiesMap nodeId → communityId (from hybrid detection), or null
 */
export function buildSimulationGraphPrep(nodes, links, communitiesMap) {
  const nodeTypeMap = new Map(nodes.map((n) => [n.id, n.type]));

  const linkMap = new Map();
  links.forEach((link) => {
    if (!linkMap.has(link.source)) linkMap.set(link.source, []);
    if (!linkMap.has(link.target)) linkMap.set(link.target, []);
    linkMap.get(link.source).push({ target: link.target, type: link.type });
    linkMap.get(link.target).push({ target: link.source, type: link.type });
  });

  const communityMap = new Map();
  if (communitiesMap) {
    communitiesMap.forEach((communityId, nodeId) => {
      if (!communityMap.has(communityId)) {
        communityMap.set(communityId, []);
      }
      communityMap.get(communityId).push(nodeId);
    });
    communityMap.forEach((ids) => {
      ids.sort((a, b) => String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" }));
    });
  }

  return { nodeTypeMap, linkMap, communityMap };
}
