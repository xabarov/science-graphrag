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
