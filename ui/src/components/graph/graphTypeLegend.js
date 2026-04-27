/**
 * Collect unique node and relationship types for legend chips (Phase 4.4).
 * Node keys align with chip rendering: nodeKind ?? node_kind ?? type ?? "Node".
 *
 * @param {{ nodes: Array<{ type?: string, nodeKind?: string, node_kind?: string }>, edges: Array<{ type?: string }> }} graph
 * @returns {{ nodeTypes: string[], edgeTypes: string[] }}
 */
export function legendNodeKindKey(n) {
  const kind = n?.nodeKind ?? n?.node_kind ?? n?.type;
  return kind != null && String(kind).trim() ? String(kind) : "Node";
}

/**
 * @param {{ type?: string }} e
 * @returns {string}
 */
export function legendEdgeTypeKey(e) {
  return e?.type != null && String(e.type).trim() ? String(e.type) : "edge";
}

export function collectGraphTypeLegend(graph) {
  const nodeTypes = new Set();
  const edgeTypes = new Set();
  for (const n of graph.nodes || []) {
    nodeTypes.add(legendNodeKindKey(n));
  }
  for (const e of graph.edges || []) {
    edgeTypes.add(legendEdgeTypeKey(e));
  }
  return {
    nodeTypes: [...nodeTypes].sort((a, b) => a.localeCompare(b)),
    edgeTypes: [...edgeTypes].sort((a, b) => a.localeCompare(b)),
  };
}

/**
 * Counts and totals for Bloom-style overview (current payload only).
 *
 * @param {{ nodes?: object[], edges?: object[] }} graph
 * @returns {{
 *   totalNodes: number,
 *   totalEdges: number,
 *   nodeKindCounts: Map<string, number>,
 *   edgeTypeCounts: Map<string, number>,
 * }}
 */
export function collectGraphComposition(graph) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const nodeKindCounts = new Map();
  const edgeTypeCounts = new Map();
  for (const n of nodes) {
    const k = legendNodeKindKey(n);
    nodeKindCounts.set(k, (nodeKindCounts.get(k) || 0) + 1);
  }
  for (const e of edges) {
    const typ = legendEdgeTypeKey(e);
    edgeTypeCounts.set(typ, (edgeTypeCounts.get(typ) || 0) + 1);
  }
  return {
    totalNodes: nodes.length,
    totalEdges: edges.length,
    nodeKindCounts,
    edgeTypeCounts,
  };
}

/**
 * @param {string[]} kinds
 * @param {Map<string, number>} counts
 * @param {"frequency" | "alphabet"} sortBy
 * @returns {string[]}
 */
export function sortLegendKinds(kinds, counts, sortBy) {
  const copy = [...kinds];
  if (sortBy === "frequency") {
    copy.sort((a, b) => {
      const db = counts.get(b) || 0;
      const da = counts.get(a) || 0;
      if (db !== da) return db - da;
      return a.localeCompare(b);
    });
  } else {
    copy.sort((a, b) => a.localeCompare(b));
  }
  return copy;
}

/**
 * @param {string[]} edgeTypes
 * @param {Map<string, number>} counts
 * @param {"frequency" | "alphabet"} sortBy
 * @returns {string[]}
 */
export function sortLegendEdgeTypes(edgeTypes, counts, sortBy) {
  return sortLegendKinds(edgeTypes, counts, sortBy);
}

export const NODE_KIND_GROUPS = {
  Work: ["Work", "WorkInternal", "WorkExternal"],
  Semantic: ["Method", "Dataset", "Claim"],
  People: ["Author"],
  Context: ["Venue", "Institution"],
};

/**
 * All kinds that belong to predefined legend groups (not "Other").
 */
export const LEGEND_GROUPED_KINDS = new Set(
  Object.values(NODE_KIND_GROUPS).flatMap((kinds) => kinds),
);

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
    const kind = legendNodeKindKey(n);
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
