import React from "react";
import Alert from "@mui/material/Alert";

/**
 * Traceability + empty graph responses (below layer counts footer).
 *
 * @param {{
 *   traceSummary: string[],
 *   projectedGraph: { nodeCount: number },
 *   t: (k: string, opts?: object) => string,
 * }} props
 */
export default function GraphWorkspaceAlertsBelowFooter({ traceSummary, projectedGraph, t }) {
  return (
    <>
      {traceSummary.length > 0 ? (
        <Alert severity="info" sx={{ mt: 1 }}>
          {t("graph.workspacePanel.traceabilityBanner", { detail: traceSummary.join(" · ") })}
        </Alert>
      ) : null}
      {projectedGraph.nodeCount === 0 ? (
        <Alert severity="info" sx={{ mt: 1 }}>
          {t("graph.workspacePanel.emptyGraphResponse")}
        </Alert>
      ) : null}
    </>
  );
}
