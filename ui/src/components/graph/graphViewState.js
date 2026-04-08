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
 * @param {unknown} value
 * @returns {string}
 */
export function normalizeGraphEdgeId(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {unknown} raw
 * @returns {{
 *   workId: string,
 *   nodes: Array<object>,
 *   edges: Array<object>,
 *   meta: object,
 *   nodeCount: number,
 *   edgeCount: number,
 *   selectedNodeId: string,
 *   warnings: string[],
 * }}
 */
export function normalizeGraphPayload(raw) {
  const warnings = [];
  const payload = raw && typeof raw === "object" ? raw : {};
  const rawNodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const rawEdges = Array.isArray(payload.edges) ? payload.edges : [];
  const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : {};

  const idUsage = new Map();
  const nodes = rawNodes.map((node, index) => {
    const baseId = node?.id == null ? `node-${index}` : String(node.id);
    const seen = idUsage.get(baseId) ?? 0;
    idUsage.set(baseId, seen + 1);
    const id = seen === 0 ? baseId : `${baseId}__dup${seen}`;
    if (seen > 0) {
      warnings.push(
        `Duplicate node id "${baseId}" was reassigned to "${id}" (first occurrence keeps "${baseId}").`,
      );
    }
    return {
      id,
      label: node?.label == null ? String(node?.id ?? `node-${index}`) : String(node.label),
      type: node?.type == null ? "Node" : String(node.type),
      raw: node && typeof node === "object" ? node : {},
    };
  });

  const nodeIdSet = new Set(nodes.map((n) => n.id));

  const normalizedEdges = rawEdges.map((edge, index) => ({
    id: edge?.id == null ? `edge-${index}` : String(edge.id),
    source: edge?.source == null ? "" : String(edge.source),
    target: edge?.target == null ? "" : String(edge.target),
    type: edge?.type == null ? "edge" : String(edge.type),
    raw: edge && typeof edge === "object" ? edge : {},
  }));

  const edges = [];
  let orphanCount = 0;
  for (const edge of normalizedEdges) {
    const srcOk = nodeIdSet.has(edge.source);
    const tgtOk = nodeIdSet.has(edge.target);
    if (srcOk && tgtOk) {
      edges.push(edge);
    } else {
      orphanCount += 1;
    }
  }
  if (orphanCount > 0) {
    warnings.push(
      `Dropped ${orphanCount} edge(s) with missing source or target node id (not present after normalization).`,
    );
  }

  return {
    workId: payload.work_id == null ? "" : String(payload.work_id),
    nodes,
    edges,
    meta,
    nodeCount: nodes.length,
    edgeCount: edges.length,
    selectedNodeId: "",
    warnings,
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
 * @param {{ edges: Array<{ id: string }> }} graph
 * @param {string} preferredEdgeId
 * @returns {string}
 */
export function resolveSelectedEdgeId(graph, preferredEdgeId = "") {
  const next = normalizeGraphEdgeId(preferredEdgeId);
  if (next && graph.edges.some((e) => e.id === next)) {
    return next;
  }
  return "";
}

/**
 * @param {{ nodes: Array<object>, edges: Array<object>, meta: object }} graph
 * @param {string} selectedNodeId
 * @param {string} [selectedEdgeId]
 * @returns {{ selectedNode: object | null, relatedEdges: Array<object>, selectedEdge: object | null }}
 */
export function deriveGraphDetail(graph, selectedNodeId, selectedEdgeId = "") {
  const eid = normalizeGraphEdgeId(selectedEdgeId);
  if (eid) {
    const selectedEdge = graph.edges.find((edge) => edge.id === eid) || null;
    if (selectedEdge) {
      return { selectedNode: null, relatedEdges: [], selectedEdge };
    }
  }
  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || null;
  const relatedEdges = selectedNode
    ? graph.edges.filter((edge) => edge.source === selectedNodeId || edge.target === selectedNodeId)
    : [];
  return { selectedNode, relatedEdges, selectedEdge: null };
}
