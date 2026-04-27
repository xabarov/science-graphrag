import { useLayoutEffect } from "react";

import { reconcileGraphWorkspaceSelection } from "../graphSelectionPolicy.js";

/**
 * Applies {@link reconcileGraphWorkspaceSelection} once per paint when props disagree
 * with resolved graph selection (replaces four chained useEffects).
 *
 * @param {{
 *   selectedNodeId: string,
 *   selectedEdgeId: string,
 *   resolvedSelectedNodeId: string,
 *   resolvedSelectedEdgeId: string,
 *   onReconcile?: (next: { nodeId: string, edgeId: string }) => void,
 * }} props
 */
export function useGraphSelectionReconcile({
  selectedNodeId,
  selectedEdgeId,
  resolvedSelectedNodeId,
  resolvedSelectedEdgeId,
  onReconcile,
}) {
  useLayoutEffect(() => {
    if (!onReconcile) return;
    const { nodeId, edgeId, changed } = reconcileGraphWorkspaceSelection({
      selectedNodeId,
      selectedEdgeId,
      resolvedSelectedNodeId,
      resolvedSelectedEdgeId,
    });
    if (!changed) return;
    onReconcile({ nodeId, edgeId });
  }, [
    onReconcile,
    selectedEdgeId,
    selectedNodeId,
    resolvedSelectedEdgeId,
    resolvedSelectedNodeId,
  ]);
}
