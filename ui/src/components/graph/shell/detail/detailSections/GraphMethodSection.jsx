import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import MarkdownViewCore from "../../../../work/markdown/MarkdownViewCore.jsx";
import { graphDetailMarkdownPanelSx } from "../graphNodeDetailSectionSx.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   methodMarkdownForViewer: string,
 *   compact: boolean,
 * }} props
 */
export default function GraphMethodSection({ tk, t, methodMarkdownForViewer, compact }) {
  if (!methodMarkdownForViewer) return null;
  return (
    <Box sx={{ mt: 2, mb: 1 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>
        {t("graph.detailPanel.methodDescription")}
      </Typography>
      <Box sx={graphDetailMarkdownPanelSx(tk, compact)}>
        <MarkdownViewCore markdown={methodMarkdownForViewer} data-testid="graph-method-markdown" />
      </Box>
    </Box>
  );
}
