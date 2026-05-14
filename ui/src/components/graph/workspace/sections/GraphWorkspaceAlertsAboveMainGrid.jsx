import React from "react";
import Alert from "@mui/material/Alert";

import { GRAPH_CAP_WARNING_LARGE_PAYLOAD } from "../../model/graphUiLimits.js";

/**
 * Normalized payload + large payload performance warnings (above main grid).
 *
 * @param {{
 *   projectedGraph: { warnings: unknown[], nodeCount?: number },
 *   capWarnings: string[],
 *   displayGraphNodes: unknown[] | undefined,
 *   displayGraphEdges: unknown[] | undefined,
 *   t: (k: string, opts?: object) => string,
 * }} props
 */
export default function GraphWorkspaceAlertsAboveMainGrid({
  projectedGraph,
  capWarnings,
  displayGraphNodes,
  displayGraphEdges,
  t,
}) {
  return (
    <>
      {projectedGraph.warnings.length > 0 ? (
        <Alert severity="info" sx={{ mb: 1 }}>
          {t("workspace.graph.normalizedPayload")}
        </Alert>
      ) : null}
      {capWarnings.includes(GRAPH_CAP_WARNING_LARGE_PAYLOAD) ? (
        <Alert severity="warning" sx={{ mb: 1 }}>
          {t("workspace.graph.warn.large_payload_performance", {
            nodes: displayGraphNodes?.length ?? 0,
            edges: displayGraphEdges?.length ?? 0,
          })}
        </Alert>
      ) : null}
    </>
  );
}
