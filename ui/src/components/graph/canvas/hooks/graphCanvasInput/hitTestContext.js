/**
 * Shared options for {@link hitTestNodeScreen} across hover pick, pointer down, and click selection.
 *
 * @param {object} deps
 * @param {string} deps.graphColorBy
 * @param {{ nodes: unknown[] }} deps.graph
 * @param {boolean} deps.searchActive
 * @param {unknown} deps.searchMatchSet
 * @param {string} deps.selectedNodeId
 * @param {string} deps.hoveredNodeId
 * @param {string} deps.canvasLabelMode
 * @param {import("react").MutableRefObject<Set<string> | null> | null} [deps.activeForLabelSetRef]
 */
export function buildNodeHitTestScreenOpts(deps) {
  const {
    graphColorBy,
    graph,
    searchActive,
    searchMatchSet,
    selectedNodeId,
    hoveredNodeId,
    canvasLabelMode,
    activeForLabelSetRef,
  } = deps;
  return {
    colorBy: graphColorBy,
    nodeCount: graph.nodes.length,
    searchActive,
    searchMatchSet: searchMatchSet instanceof Set ? searchMatchSet : null,
    selectedNodeId,
    hoveredNodeId,
    mode: canvasLabelMode,
    activeForLabelSet: activeForLabelSetRef?.current ?? null,
  };
}
