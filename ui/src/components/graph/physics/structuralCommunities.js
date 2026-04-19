/**
 * Structural community detection (label propagation), ported from osint-gr clustering.js.
 * No OSINT-specific hybrid / personId logic.
 */

/**
 * @param {Array<{ id: string }>} nodes
 * @param {Array<{ source: string, target: string }>} links
 * @param {number} [maxIterations]
 * @returns {Map<string, string>}
 */
export function detectCommunities(nodes, links, maxIterations = 10) {
  if (nodes.length === 0) return new Map();

  const communities = new Map();
  nodes.forEach((node) => {
    communities.set(node.id, node.id);
  });

  const adjacency = new Map();
  nodes.forEach((node) => {
    adjacency.set(node.id, []);
  });

  links.forEach((link) => {
    if (adjacency.has(link.source) && adjacency.has(link.target)) {
      adjacency.get(link.source).push(link.target);
      adjacency.get(link.target).push(link.source);
    }
  });

  let changed = true;
  let iterations = 0;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations += 1;

    const ordered = [...nodes].sort((a, b) => String(a.id).localeCompare(String(b.id)));

    for (const node of ordered) {
      const neighbors = adjacency.get(node.id) || [];
      if (neighbors.length === 0) continue;

      const labelCounts = new Map();
      neighbors.forEach((neighborId) => {
        const label = communities.get(neighborId);
        labelCounts.set(label, (labelCounts.get(label) || 0) + 1);
      });

      let maxCount = 0;
      let mostFrequentLabel = communities.get(node.id);

      labelCounts.forEach((count, label) => {
        if (count > maxCount || (count === maxCount && String(label).localeCompare(String(mostFrequentLabel)) < 0)) {
          maxCount = count;
          mostFrequentLabel = label;
        }
      });

      if (mostFrequentLabel !== communities.get(node.id)) {
        communities.set(node.id, mostFrequentLabel);
        changed = true;
      }
    }
  }

  return communities;
}

/**
 * @param {string} nodeId
 * @param {Map<string, string>} communities
 * @returns {string | null}
 */
export function getNodeCluster(nodeId, communities) {
  return communities.get(nodeId) || null;
}
