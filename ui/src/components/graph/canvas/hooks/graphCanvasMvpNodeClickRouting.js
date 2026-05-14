/**
 * Pure routing for graph canvas node pointer selection (Aggregator expand vs normal select).
 *
 * @param {{
 *   nodeById: Map<string, { id?: string, nodeKind?: string, raw?: { aggregation_hints?: { expand_endpoint?: string } } }>,
 *   nodeId: string,
 *   onAggregatorExpand?: (node: unknown, expandUrl: string) => void,
 *   onSelectNode?: (nodeId: string) => void,
 * }} args
 */
export function routeGraphCanvasNodeClick({ nodeById, nodeId, onAggregatorExpand, onSelectNode }) {
  const clickedNode = nodeById.get(nodeId);
  if (clickedNode?.nodeKind === "Aggregator") {
    const expandUrl = clickedNode.raw?.aggregation_hints?.expand_endpoint;
    if (expandUrl) {
      onAggregatorExpand?.(clickedNode, expandUrl);
      return;
    }
  }
  onSelectNode?.(nodeId);
}
