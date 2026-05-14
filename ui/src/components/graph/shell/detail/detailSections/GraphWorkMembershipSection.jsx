import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../../common/index.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   onExpandWorkspaceNeighbors?: () => void | Promise<void>,
 *   expandWorkspaceNeighborsBusy?: boolean,
 * }} props
 */
export default function GraphWorkMembershipSection({
  tk,
  t,
  selectedNode,
  onExpandWorkspaceNeighbors,
  expandWorkspaceNeighborsBusy = false,
}) {
  const showCiteRow =
    String(selectedNode.type) === "Work" &&
    (selectedNode.workspaceMembership || selectedNode.internalCiteCount != null || selectedNode.externalCiteCount != null);

  const showExpand =
    onExpandWorkspaceNeighbors && String(selectedNode.type) === "Work" && Number(selectedNode.externalCiteCount) > 0;

  if (!showCiteRow && !showExpand) return null;

  return (
    <>
      {showCiteRow ? (
        <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          {selectedNode.workspaceMembership ? (
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, fontFamily: "monospace" }}>
              {String(selectedNode.workspaceMembership)}
            </Typography>
          ) : null}
          {selectedNode.internalCiteCount != null ? (
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.accent }}>
              {t("graph.detailPanel.intCites", { count: String(selectedNode.internalCiteCount) })}
            </Typography>
          ) : null}
          {selectedNode.externalCiteCount != null ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(251,191,36,0.85)" }}>
              {t("graph.detailPanel.extCites", { count: String(selectedNode.externalCiteCount) })}
            </Typography>
          ) : null}
        </Box>
      ) : null}
      {showExpand ? (
        <Box sx={{ mt: 1 }}>
          <CursorSmallButton type="button" disabled={expandWorkspaceNeighborsBusy} onClick={() => onExpandWorkspaceNeighbors()}>
            {expandWorkspaceNeighborsBusy
              ? t("graph.detailPanel.loading")
              : t("graph.detailPanel.expandExternal", { count: String(selectedNode.externalCiteCount) })}
          </CursorSmallButton>
        </Box>
      ) : null}
    </>
  );
}
