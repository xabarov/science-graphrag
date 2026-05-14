import React from "react";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../../common/index.js";
import { localizeAggregatorSubtitle, localizeAggregatorTitle } from "../../../model/graphLocalize.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   onAggregatorExpand?: (node: object, expandEndpoint: string) => void | Promise<void>,
 *   expandWorkspaceNeighborsBusy?: boolean,
 * }} props
 */
export default function GraphAggregatorSection({
  tk,
  t,
  selectedNode,
  onAggregatorExpand,
  expandWorkspaceNeighborsBusy = false,
}) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>{t("graph.aggregator.badge")}</Typography>
      <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25 }}>
        {localizeAggregatorTitle(selectedNode, t)}
      </Typography>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>{localizeAggregatorSubtitle(t)}</Typography>
      {Array.isArray(selectedNode.raw?.aggregation_hints?.preview_labels) &&
      selectedNode.raw.aggregation_hints.preview_labels.length > 0 ? (
        <List dense sx={{ py: 0.5 }}>
          {selectedNode.raw.aggregation_hints.preview_labels.map((label) => (
            <ListItem key={String(label)} sx={{ px: 0 }}>
              <ListItemText primary={String(label)} primaryTypographyProps={{ sx: { color: tk.text.primary } }} />
            </ListItem>
          ))}
        </List>
      ) : null}
      <CursorSmallButton
        type="button"
        disabled={expandWorkspaceNeighborsBusy}
        onClick={() => onAggregatorExpand?.(selectedNode, String(selectedNode.raw?.aggregation_hints?.expand_endpoint || ""))}
      >
        {expandWorkspaceNeighborsBusy
          ? t("graph.aggregator.loading")
          : t("graph.aggregator.expandAll", {
              count: String(selectedNode.raw?.aggregation_hints?.count || 0),
            })}
      </CursorSmallButton>
    </Box>
  );
}
