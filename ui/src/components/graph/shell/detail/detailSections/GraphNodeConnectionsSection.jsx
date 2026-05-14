import React from "react";
import Typography from "@mui/material/Typography";

import NodeConnectionsList from "../NodeConnectionsList.jsx";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   rows: Array<object>,
 *   relatedEdges: Array<object>,
 *   onSelectEdge?: (edgeId: string) => void,
 * }} props
 */
export default function GraphNodeConnectionsSection({ tk, t, rows, relatedEdges, onSelectEdge }) {
  return (
    <>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 1.5, mb: 0.75, color: tk.text.primary }}>
        {t("graph.detailPanel.connections")}
      </Typography>
      <NodeConnectionsList tk={tk} t={t} rows={rows} relatedEdges={relatedEdges} onSelectEdge={onSelectEdge} />
    </>
  );
}
