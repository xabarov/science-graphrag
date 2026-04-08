/**
 * Client-side caps for graph visualization (cards + canvas). Full counts stay on the normalized graph object.
 */

export const GRAPH_UI_MAX_NODES = 150;
export const GRAPH_UI_MAX_EDGES = 350;

/**
 * Returns a shallow copy of the graph with truncated nodes/edges for rendering only.
 * If `preferredNodeId` is set and would be dropped by the node cap, it replaces the last slot so selection stays visible.
 *
 * @param {{ nodes: Array<object>, edges: Array<object> }} graph normalized graph
 * @param {string} [preferredNodeId] resolved selection (may be empty)
 * @returns {{ displayGraph: object, capWarnings: string[] }}
 */
export function capGraphForUi(graph, preferredNodeId = "") {
  const capWarnings = [];
  const fullNodes = graph.nodes.length;
  const fullEdges = graph.edges.length;
  let nodes = graph.nodes;
  let edges = graph.edges;
  const pref = String(preferredNodeId || "").trim();

  if (fullNodes > GRAPH_UI_MAX_NODES) {
    let picked = graph.nodes.slice(0, GRAPH_UI_MAX_NODES);
    if (pref) {
      const inPicked = picked.some((n) => n.id === pref);
      if (!inPicked) {
        const extra = graph.nodes.find((n) => n.id === pref);
        if (extra) {
          picked = [...picked.slice(0, GRAPH_UI_MAX_NODES - 1), extra];
        }
      }
    }
    nodes = picked;
    capWarnings.push(
      `Performance cap: showing ${nodes.length} of ${fullNodes} nodes (full counts in chips below).`,
    );
  }

  const idSet = new Set(nodes.map((n) => n.id));
  edges = graph.edges.filter((e) => idSet.has(e.source) && idSet.has(e.target));

  if (edges.length > GRAPH_UI_MAX_EDGES) {
    capWarnings.push(
      `Performance cap: showing ${GRAPH_UI_MAX_EDGES} of ${fullEdges} edges (full counts in chips below).`,
    );
    edges = edges.slice(0, GRAPH_UI_MAX_EDGES);
  }

  return {
    displayGraph: { ...graph, nodes, edges },
    capWarnings,
  };
}
