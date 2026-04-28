import { useCallback, useMemo } from "react";

import { projectAuthorSemanticGraph } from "../../model/authorSemanticProjection.js";
import { applyGraphVisibilityFilter } from "../../model/graphVisibilityFilter.js";
import { deriveInspectorDetail } from "../../model/graphInspectorModel.js";
import { localizeEdgeType } from "../../model/graphLocalize.js";
import { filterNodeIdsBySearchSubstring } from "../../model/graphNodeSearch.js";
import { capGraphForUi } from "../../model/graphUiLimits.js";
import {
  normalizeGraphEdgeId,
  normalizeGraphNodeId,
  resolveSelectedEdgeId,
  resolveSelectedNodeId,
} from "../../model/graphViewState.js";

/**
 * @param {{
 *   graph: object,
 *   graphVisibility: import("../../model/graphVisibilityFilter.js").GraphVisibilityValue,
 *   selectedNodeId: string,
 *   selectedEdgeId: string,
 *   localFindQuery: string,
 *   t: (key: string, ...args: unknown[]) => string,
 * }} input
 */
export function useGraphWorkspaceProjection({
  graph,
  graphVisibility,
  selectedNodeId,
  selectedEdgeId,
  localFindQuery,
  t,
}) {
  const edgeTypeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);

  const projectedGraph = useMemo(() => projectAuthorSemanticGraph(graph), [graph]);
  const { graph: visibleGraph, stats: visibilityStats } = useMemo(
    () => applyGraphVisibilityFilter(projectedGraph, graphVisibility),
    [projectedGraph, graphVisibility],
  );
  const projectedResolvedNodeId = useMemo(
    () => resolveSelectedNodeId(projectedGraph, normalizeGraphNodeId(selectedNodeId)),
    [projectedGraph, selectedNodeId],
  );
  const resolvedSelectedEdgeId = useMemo(
    () => resolveSelectedEdgeId(projectedGraph, normalizeGraphEdgeId(selectedEdgeId)),
    [projectedGraph, selectedEdgeId],
  );
  const resolvedSelectedNodeId = useMemo(() => {
    if (resolvedSelectedEdgeId) return "";
    const pref = normalizeGraphNodeId(projectedResolvedNodeId);
    if (!pref) return resolveSelectedNodeId(visibleGraph, "");
    if (visibleGraph.nodes.some((n) => n.id === pref)) return pref;
    // Keep URL selection when the node exists in the loaded graph but is hidden by the type filter
    // (detail panel uses projected graph; otherwise reconcile would snap the URL to another node).
    if (projectedGraph.nodes.some((n) => n.id === pref)) return pref;
    return resolveSelectedNodeId(visibleGraph, "");
  }, [visibleGraph, projectedGraph, projectedResolvedNodeId, resolvedSelectedEdgeId]);
  const { displayGraph, capWarnings } = useMemo(
    () => capGraphForUi(visibleGraph, resolvedSelectedNodeId),
    [visibleGraph, resolvedSelectedNodeId],
  );
  const inspector = useMemo(
    () => deriveInspectorDetail(projectedGraph, projectedResolvedNodeId, resolvedSelectedEdgeId, { edgeTypeLabel }),
    [projectedGraph, edgeTypeLabel, projectedResolvedNodeId, resolvedSelectedEdgeId],
  );
  const nodeSearchMatchIds = useMemo(
    () => filterNodeIdsBySearchSubstring(displayGraph.nodes, localFindQuery),
    [displayGraph.nodes, localFindQuery],
  );

  return {
    projectedResolvedNodeId,
    projectedGraph,
    visibleGraph,
    visibilityStats,
    resolvedSelectedEdgeId,
    resolvedSelectedNodeId,
    displayGraph,
    capWarnings,
    inspector,
    nodeSearchMatchIds,
  };
}
