import { useCallback } from "react";

/**
 * Selection, keyboard clear, toolbar view actions (fit / zoom / center on selection).
 *
 * @param {{
 *   graph: { edges?: Array<{ id: string, source: string, target: string }> },
 *   selectedNodeId: string,
 *   selectedEdgeId: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 *   fitView: (opts?: object) => void | Promise<void>,
 *   zoomTo: (zoom: number, opts?: object) => void | Promise<void>,
 * }} opts
 */
export function useGraphFlowSelectionHandlers({
  graph,
  selectedNodeId,
  selectedEdgeId,
  onSelectNode,
  onSelectEdge,
  fitView,
  zoomTo,
}) {
  const handleFitAll = useCallback(() => {
    void fitView({ padding: 0.2, duration: 200 });
  }, [fitView]);

  const handleResetZoom = useCallback(() => {
    void zoomTo(1, { duration: 150 });
  }, [zoomTo]);

  const handleCenterSelection = useCallback(() => {
    const nodeId = String(selectedNodeId || "").trim();
    const edgeId = String(selectedEdgeId || "").trim();
    if (nodeId) {
      void fitView({
        nodes: [{ id: nodeId }],
        padding: 0.35,
        duration: 250,
        maxZoom: 2,
      });
      return;
    }
    if (edgeId) {
      const graphEdges = Array.isArray(graph?.edges) ? graph.edges : [];
      const e = graphEdges.find((ed) => ed.id === edgeId);
      if (e) {
        void fitView({
          nodes: [{ id: e.source }, { id: e.target }],
          padding: 0.4,
          duration: 250,
        });
      }
    }
  }, [fitView, graph, selectedEdgeId, selectedNodeId]);

  const onNodeClick = useCallback(
    (_evt, node) => {
      onSelectNode?.(node.id);
    },
    [onSelectNode],
  );

  const onEdgeClick = useCallback(
    (_evt, edge) => {
      onSelectEdge?.(edge.id);
    },
    [onSelectEdge],
  );

  const onPaneClick = useCallback(() => {
    onSelectNode?.("");
    onSelectEdge?.("");
  }, [onSelectEdge, onSelectNode]);

  const handleKeyDown = useCallback(
    (ev) => {
      if (ev.key === "Escape") {
        ev.preventDefault();
        onSelectNode?.("");
        onSelectEdge?.("");
      }
    },
    [onSelectEdge, onSelectNode],
  );

  const liveRegionText =
    selectedEdgeId && String(selectedEdgeId).trim()
      ? `Edge ${String(selectedEdgeId).trim()} selected.`
      : selectedNodeId && String(selectedNodeId).trim()
        ? `Node ${String(selectedNodeId).trim()} selected.`
        : "No node or edge selected.";

  const canCenter = Boolean(String(selectedNodeId || "").trim() || String(selectedEdgeId || "").trim());

  return {
    handleFitAll,
    handleResetZoom,
    handleCenterSelection,
    onNodeClick,
    onEdgeClick,
    onPaneClick,
    handleKeyDown,
    liveRegionText,
    canCenter,
  };
}
