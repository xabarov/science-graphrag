/**
 * Collect unique node and relationship types for legend chips (Phase 4.4).
 * @param {{ nodes: Array<{ type?: string }>, edges: Array<{ type?: string }> }} graph
 * @returns {{ nodeTypes: string[], edgeTypes: string[] }}
 */
export function collectGraphTypeLegend(graph) {
  const nodeTypes = new Set();
  const edgeTypes = new Set();
  for (const n of graph.nodes || []) {
    nodeTypes.add(n?.type != null && String(n.type).trim() ? String(n.type) : "Node");
  }
  for (const e of graph.edges || []) {
    edgeTypes.add(e?.type != null && String(e.type).trim() ? String(e.type) : "edge");
  }
  return {
    nodeTypes: [...nodeTypes].sort((a, b) => a.localeCompare(b)),
    edgeTypes: [...edgeTypes].sort((a, b) => a.localeCompare(b)),
  };
}

export const NODE_KIND_GROUPS = {
  Work: ["Work", "WorkInternal", "WorkExternal"],
  Semantic: ["Method", "Dataset"],
  People: ["Author", "AuthorshipReification", "Authorship"],
  Context: ["Venue", "Institution"],
};

/**
 * Group `nodeKind` values into semantic buckets for legend rendering.
 * @param {{ nodes: Array<{ type?: string, nodeKind?: string }> }} graph
 * @returns {Record<string, string[]>}
 */
export function collectGraphTypeLegendByKind(graph) {
  const grouped = {};
  const known = new Map();
  for (const [group, kinds] of Object.entries(NODE_KIND_GROUPS)) {
    grouped[group] = [];
    for (const kind of kinds) known.set(kind, group);
  }

  for (const n of graph.nodes || []) {
    const kind = n?.nodeKind != null && String(n.nodeKind).trim()
      ? String(n.nodeKind)
      : n?.type != null && String(n.type).trim()
        ? String(n.type)
        : "Node";
    const group = known.get(kind) || "Other";
    if (!grouped[group]) grouped[group] = [];
    if (!grouped[group].includes(kind)) grouped[group].push(kind);
  }

  for (const group of Object.keys(grouped)) {
    grouped[group].sort((a, b) => a.localeCompare(b));
    if (grouped[group].length === 0) delete grouped[group];
  }
  return grouped;
}
