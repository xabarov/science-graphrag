import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../common/index.js";
import { localizeEdgeType } from "../../model/graphLocalize.js";
import ContradictionDetailBody from "./ContradictionDetailBody.jsx";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedEdge: object,
 *   selectedEdgeReadable: string,
 *   isContradictsEdge: boolean,
 *   onSelectNode?: (nodeId: string) => void,
 *   contradictionPayload: Record<string, unknown> | null,
 *   contradictionBusy: boolean,
 *   contradictionError: string,
 *   effectiveWorkspaceId: string,
 * }} props
 */
export default function GraphEdgeDetailSection({
  tk,
  t,
  selectedEdge,
  selectedEdgeReadable,
  isContradictsEdge,
  onSelectNode,
  contradictionPayload,
  contradictionBusy,
  contradictionError,
  effectiveWorkspaceId,
}) {
  return (
    <>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>
        {t("graph.detailPanel.relationship")}
      </Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, lineHeight: 1.45, mb: 1 }}>
        {selectedEdgeReadable ||
          `${selectedEdge.sourceLabel || selectedEdge.source} —[${localizeEdgeType(selectedEdge, t)}]→ ${
            selectedEdge.targetLabel || selectedEdge.target
          }`}
      </Typography>
      <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent, mb: 0.5 }}>{localizeEdgeType(selectedEdge, t)}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1 }}>
        <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.source)}>
          {t("graph.detailPanel.openSource")}
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.target)}>
          {t("graph.detailPanel.openTarget")}
        </CursorSmallButton>
      </Box>
      <Typography sx={{ fontSize: "0.7rem", color: tk.text.faint, fontFamily: "monospace", wordBreak: "break-all" }}>
        id: {selectedEdge.id}
      </Typography>
      {isContradictsEdge ? (
        <Box sx={{ mt: 1.5 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", mb: 0.75, color: tk.text.secondary }}>
            {t("graph.detailPanel.contradictionHeading")}
          </Typography>
          <ContradictionDetailBody
            tk={tk}
            t={t}
            selectedEdge={selectedEdge}
            contradictionPayload={contradictionPayload}
            contradictionBusy={contradictionBusy}
            contradictionError={contradictionError}
            effectiveWorkspaceId={effectiveWorkspaceId}
          />
        </Box>
      ) : null}
    </>
  );
}
