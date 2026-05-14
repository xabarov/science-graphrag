import React from "react";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../../common/index.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   authorAuthoredWorks: Array<object>,
 *   compact: boolean,
 *   onSelectNode?: (nodeId: string) => void,
 * }} props
 */
export default function GraphAuthorWorksSection({ tk, t, selectedNode, authorAuthoredWorks, compact, onSelectNode }) {
  if (
    !selectedNode ||
    !(String(selectedNode.type) === "Author" || String(selectedNode.nodeKind) === "Author") ||
    authorAuthoredWorks.length === 0
  ) {
    return null;
  }

  return (
    <Box sx={{ mt: 2 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.75, color: tk.text.primary }}>
        {t("graph.detailPanel.authorWorks")}
      </Typography>
      <List dense sx={{ py: 0, maxHeight: compact ? 200 : 260, overflow: "auto" }}>
        {authorAuthoredWorks.map((row) => (
          <ListItem
            key={row.workId}
            sx={{
              px: 0,
              py: 0.75,
              alignItems: "flex-start",
              flexDirection: "column",
              gap: 0.5,
              borderBottom: `1px solid ${tk.border.default}`,
            }}
          >
            <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75, width: "100%" }}>
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, minWidth: 0 }}>{row.workLabel}</Typography>
              <CursorSmallButton type="button" onClick={() => onSelectNode?.(row.workId)}>
                {t("graph.detailPanel.authorWorkOpen")}
              </CursorSmallButton>
            </Box>
            {row.authorPosition != null && String(row.authorPosition).trim() !== "" ? (
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary }}>
                {t("graph.detailPanel.authorPosition", { position: String(row.authorPosition) })}
              </Typography>
            ) : null}
            {row.isCorresponding === true || row.isCorresponding === "true" ? (
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.accent }}>{t("graph.detailPanel.authorCorresponding")}</Typography>
            ) : null}
            {row.rawAffiliation != null && String(row.rawAffiliation).trim() !== "" ? (
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.4 }}>
                {t("graph.detailPanel.authorAffiliation")}: {String(row.rawAffiliation)}
              </Typography>
            ) : null}
          </ListItem>
        ))}
      </List>
    </Box>
  );
}
