/**
 * Stable warning code for i18n: `workspace.graph.warn.${GRAPH_CAP_WARNING_LARGE_PAYLOAD}`.
 */
export const GRAPH_CAP_WARNING_LARGE_PAYLOAD = "large_payload_performance";

/** Above these counts, show a non-blocking perf warning (full graph still rendered). */
export const WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT = 5000;
export const WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT = 10000;

/**
 * UI display cap was removed: always render the full visible graph after filters.
 * Optional performance warnings (non-truncating) surface above warn thresholds.
 *
 * @param {{ nodes?: Array<object>, edges?: Array<object> } | null | undefined} graph normalized graph
 * @param {string} [preferredNodeId] reserved for future neighborhood-preserving caps
 * @returns {{ displayGraph: object, capWarnings: string[] }} capWarnings are stable codes for i18n
 */
export function capGraphForUi(graph, preferredNodeId = "") {
  void preferredNodeId;
  const raw = graph && typeof graph === "object" ? graph : null;
  const nodes = Array.isArray(raw?.nodes) ? raw.nodes : [];
  const edges = Array.isArray(raw?.edges) ? raw.edges : [];
  /** @type {string[]} */
  const capWarnings = [];
  if (
    nodes.length >= WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT ||
    edges.length >= WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT
  ) {
    capWarnings.push(GRAPH_CAP_WARNING_LARGE_PAYLOAD);
  }
  const displayGraph = raw ?? { nodes: [], edges: [] };
  return { displayGraph, capWarnings };
}
