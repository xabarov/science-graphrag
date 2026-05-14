import { useMemo } from "react";

import { detectCommunitiesForUi } from "../../canvas/physics/structuralCommunities.js";

/**
 * @param {{ displayGraph: { nodes?: unknown[], edges?: unknown[] } }} opts
 */
export function useGraphWorkspacePanelCommunityMap({ displayGraph }) {
  const displayGraphNodes = displayGraph?.nodes;
  const displayGraphEdges = displayGraph?.edges;

  return useMemo(() => {
    const nodes = displayGraphNodes || [];
    const edges = displayGraphEdges || [];
    if (!nodes.length) return new Map();
    const simNodes = nodes.map((n) => ({
      id: n.id,
      type: n.type == null ? "Node" : String(n.type),
      workspaceMembership: n.workspaceMembership == null ? "" : String(n.workspaceMembership).trim().toLowerCase(),
    }));
    const simLinks = edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type == null ? "edge" : String(e.type),
    }));
    return detectCommunitiesForUi(simNodes, simLinks);
  }, [displayGraphNodes, displayGraphEdges]);
}
