/**
 * Structural community detection (label propagation), ported from osint-gr clustering.js.
 * No OSINT-specific hybrid / personId logic.
 */

import { detectScienceHybridCommunities } from "./scienceHybridCommunities.js";
import { COMMUNITY_DETECTION_MAX_LINKS, COMMUNITY_DETECTION_MAX_NODES } from "./simConstants.js";

/** Edge types used for thematic LPA inside {@link detectCommunitiesForUi}. */
export const LPA_TOPIC_EDGE_TYPES = new Set(["USES_METHOD", "EVALUATED_ON", "CITES", "PUBLISHED_IN"]);

const DEFAULT_LPA_SPLIT_RATIO = 0.3;

/**
 * @param {Array<{ source: string, target: string, type?: string }>} links
 * @returns {Array<{ source: string, target: string }>}
 */
export function filterTopicLinksForLpa(links) {
  const out = [];
  (links || []).forEach((l) => {
    const t = l.type == null ? "" : String(l.type);
    if (LPA_TOPIC_EDGE_TYPES.has(t)) {
      out.push({ source: String(l.source), target: String(l.target) });
    }
  });
  return out;
}

/**
 * Hybrid authorship clusters + optional LPA split on thematic edges (Wave GR-COM-1).
 *
 * @param {Array<{ id: string, type?: string, workspaceMembership?: string }>} nodes
 * @param {Array<{ source: string, target: string, type?: string }>} links
 * @param {{ maxLpaIterations?: number, lpaSplitRatio?: number }} [options]
 * @returns {Map<string, string>} nodeId -> stable UI community id
 */
export function detectCommunitiesForUi(nodes, links, options = {}) {
  const maxLpaIterations = Number.isFinite(options.maxLpaIterations) ? options.maxLpaIterations : 10;
  const lpaSplitRatio =
    typeof options.lpaSplitRatio === "number" && options.lpaSplitRatio >= 0 && options.lpaSplitRatio <= 1
      ? options.lpaSplitRatio
      : DEFAULT_LPA_SPLIT_RATIO;

  if (!Array.isArray(nodes) || nodes.length === 0) return new Map();

  const linkArr = Array.isArray(links) ? links : [];
  if (nodes.length > COMMUNITY_DETECTION_MAX_NODES || linkArr.length > COMMUNITY_DETECTION_MAX_LINKS) {
    /** @type {Map<string, string>} */
    const cheap = new Map();
    nodes.forEach((n) => cheap.set(String(n.id), `type:${String(n.type || "Node")}`));
    return cheap;
  }

  const hybrid = detectScienceHybridCommunities(nodes, links);
  const topicLinks = filterTopicLinksForLpa(links);
  const lpaNodes = nodes.map((n) => ({ id: String(n.id) }));
  const lpaLabels = detectCommunities(lpaNodes, topicLinks, maxLpaIterations);

  const nodeIds = nodes.map((n) => String(n.id));
  const idSet = new Set(nodeIds);

  /** @type {Map<string, Set<string>>} */
  const hybridMembers = new Map();
  nodeIds.forEach((id) => {
    const h = hybrid.get(id) != null ? String(hybrid.get(id)) : id;
    if (!hybridMembers.has(h)) hybridMembers.set(h, new Set());
    hybridMembers.get(h).add(id);
  });

  /** @type {Map<string, number>} */
  const topicEdgeCountInGroup = new Map();
  topicLinks.forEach((l) => {
    if (!idSet.has(l.source) || !idSet.has(l.target)) return;
    const h0 = String(hybrid.get(l.source) ?? l.source);
    const h1 = String(hybrid.get(l.target) ?? l.target);
    if (h0 !== h1) return;
    topicEdgeCountInGroup.set(h0, (topicEdgeCountInGroup.get(h0) || 0) + 1);
  });

  const out = new Map();

  hybridMembers.forEach((memberSet, hybridId) => {
    const members = [...memberSet].sort((a, b) => a.localeCompare(b));
    const size = members.length;
    if (size === 0) return;

    const internalTopicEdges = topicEdgeCountInGroup.get(hybridId) || 0;
    if (internalTopicEdges === 0) {
      members.forEach((id) => out.set(id, hybridId));
      return;
    }

    const labelCounts = new Map();
    members.forEach((id) => {
      const lab = String(lpaLabels.get(id) ?? id);
      labelCounts.set(lab, (labelCounts.get(lab) || 0) + 1);
    });

    const rankedLabels = [...labelCounts.entries()].sort(
      (a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])),
    );
    const pluralityLabel = rankedLabels.length > 0 ? String(rankedLabels[0][0]) : String(members[0]);

    let diff = 0;
    members.forEach((id) => {
      const lab = String(lpaLabels.get(id) ?? id);
      if (lab !== pluralityLabel) diff += 1;
    });
    const ratio = size > 0 ? diff / size : 0;

    if (ratio > lpaSplitRatio) {
      members.forEach((id) => {
        const lab = String(lpaLabels.get(id) ?? id);
        out.set(id, `${hybridId}\u0001lpa\u0001${lab}`);
      });
    } else {
      members.forEach((id) => out.set(id, hybridId));
    }
  });

  return out;
}

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
