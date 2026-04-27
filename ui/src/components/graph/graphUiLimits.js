/**
 * UI caps were removed for workspace/work graphs: render the full visible graph.
 *
 * @param {{ nodes: Array<object>, edges: Array<object> }} graph normalized graph
 * @param {string} [preferredNodeId] resolved selection (may be empty)
 * @returns {{ displayGraph: object, capWarnings: string[] }}
 */
export function capGraphForUi(graph, preferredNodeId = "") {
  void preferredNodeId;
  return { displayGraph: graph, capWarnings: [] };
}
