/**
 * Graph helpers for route state and lightweight visualization.
 */

/**
 * @param {unknown} value
 * @returns {string}
 */
export function normalizeGraphNodeId(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {unknown} raw
 * @returns {{workId: string, nodes: Array<object>, edges: Array<object>, meta: object, nodeCount: number, edgeCount: number, selectedNodeId: string}}
 */
export function normalizeGraphPayload(raw) {
  const payload = raw && typeof raw === "object" ? raw : {};
  const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const edges = Array.isArray(payload.edges) ? payload.edges : [];
  const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {};
  return {
    workId: payload.work_id == null ? "" : String(payload.work_id),
    nodes: nodes.map((node, index) => ({
      id: node?.id == null ? `node-${index}` : String(node.id),
      label: node?.label == null ? String(node?.id ?? `node-${index}`) : String(node.label),
      type: node?.type == null ? "Node" : String(node.type),
      raw: node && typeof node === "object" ? node : {},
    })),
    edges: edges.map((edge, index) => ({
      id: edge?.id == null ? `edge-${index}` : String(edge.id),
      source: edge?.source == null ? "" : String(edge.source),
      target: edge?.target == null ? "" : String(edge.target),
      type: edge?.type == null ? "edge" : String(edge.type),
      raw: edge && typeof edge === "object" ? edge : {},
    })),
    meta,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    selectedNodeId: "",
  };
}

/**
 * @param {{ nodes: Array<{id: string}> }} graph
 * @param {string} preferredNodeId
 * @returns {string}
 */
export function resolveSelectedNodeId(graph, preferredNodeId = "") {
  const next = normalizeGraphNodeId(preferredNodeId);
  if (next && graph.nodes.some((node) => node.id === next)) {
    return next;
  }
  return graph.nodes[0]?.id || "";
}

/**
 * @param {{ nodes: Array<object>, edges: Array<object>, meta: object }} graph
 * @param {string} selectedNodeId
 * @returns {{selectedNode: object | null, relatedEdges: Array<object>}}
 */
export function deriveGraphDetail(graph, selectedNodeId) {
  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || null;
  const relatedEdges = graph.edges.filter((edge) => edge.source === selectedNodeId || edge.target === selectedNodeId);
  return { selectedNode, relatedEdges };
}
