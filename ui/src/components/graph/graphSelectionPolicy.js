import { normalizeGraphEdgeId, normalizeGraphNodeId } from "./graphViewState.js";

/**
 * Reconcile URL/prop selection with resolved ids in the visible graph (same rules
 * as the former four useEffects in GraphWorkspacePanel).
 *
 * @param {{
 *   selectedNodeId: string,
 *   selectedEdgeId: string,
 *   resolvedSelectedNodeId: string,
 *   resolvedSelectedEdgeId: string,
 * }} input
 * @returns {{ nodeId: string, edgeId: string, changed: boolean }}
 */
export function reconcileGraphWorkspaceSelection(input) {
  const {
    selectedNodeId,
    selectedEdgeId,
    resolvedSelectedNodeId,
    resolvedSelectedEdgeId,
  } = input;
  const sn0 = normalizeGraphNodeId(selectedNodeId);
  const se0 = normalizeGraphEdgeId(selectedEdgeId);
  const rn = normalizeGraphNodeId(resolvedSelectedNodeId);
  const re = normalizeGraphEdgeId(resolvedSelectedEdgeId);

  let node = sn0;
  let edge = se0;

  if (rn && rn !== sn0) node = rn;
  if (se0 && !re) edge = "";
  if (re && sn0) node = "";
  if (rn && se0) edge = "";

  const changed = node !== sn0 || edge !== se0;
  return { nodeId: node, edgeId: edge, changed };
}
