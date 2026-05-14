import { useCallback } from "react";

import { firstMatchingNodeIdInOrder } from "../../model/graphNodeSearch.js";

/**
 * Selection + canvas focus actions for the workspace graph shell.
 *
 * @param {{
 *   detailsVisible: boolean,
 *   setDetailsVisible: React.Dispatch<React.SetStateAction<boolean>>,
 *   onSelectNode?: (id: string) => void,
 *   onSelectEdge?: (id: string) => void,
 *   displayGraph: { nodes?: unknown[] },
 *   nodeSearchMatchIds: Set<string>,
 *   setGraphColorBy: (v: string) => void,
 *   setGraphCommunityHulls: React.Dispatch<React.SetStateAction<boolean>>,
 *   setCenterCanvasNodeId: React.Dispatch<React.SetStateAction<string>>,
 *   setCenterCanvasNonce: React.Dispatch<React.SetStateAction<number>>,
 * }} opts
 */
export function useGraphWorkspacePanelActions({
  detailsVisible,
  setDetailsVisible,
  onSelectNode,
  onSelectEdge,
  displayGraph,
  nodeSearchMatchIds,
  setGraphColorBy,
  setGraphCommunityHulls,
  setCenterCanvasNodeId,
  setCenterCanvasNonce,
}) {
  const handleGraphColorByChange = useCallback(
    (v) => {
      setGraphColorBy(v);
      if (v === "type") setGraphCommunityHulls(false);
    },
    [setGraphColorBy, setGraphCommunityHulls],
  );

  const openDetailsOnSelection = useCallback(() => {
    if (!detailsVisible) setDetailsVisible(true);
  }, [detailsVisible, setDetailsVisible]);

  const handleSelectNode = useCallback(
    (id) => {
      if (String(id || "").trim()) openDetailsOnSelection();
      onSelectNode?.(id);
    },
    [onSelectNode, openDetailsOnSelection],
  );

  const handleSelectEdge = useCallback(
    (id) => {
      if (String(id || "").trim()) openDetailsOnSelection();
      onSelectEdge?.(id);
    },
    [onSelectEdge, openDetailsOnSelection],
  );

  const focusFirstLocalMatch = useCallback(() => {
    const nodes = Array.isArray(displayGraph?.nodes) ? displayGraph.nodes : [];
    const first = firstMatchingNodeIdInOrder(nodes, nodeSearchMatchIds);
    if (!first) return;
    openDetailsOnSelection();
    onSelectNode?.(first);
    setCenterCanvasNodeId(first);
    setCenterCanvasNonce((n) => n + 1);
  }, [displayGraph, nodeSearchMatchIds, onSelectNode, openDetailsOnSelection, setCenterCanvasNodeId, setCenterCanvasNonce]);

  return {
    handleGraphColorByChange,
    handleSelectNode,
    handleSelectEdge,
    focusFirstLocalMatch,
  };
}
