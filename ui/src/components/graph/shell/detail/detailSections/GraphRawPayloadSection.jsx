import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../../../common/index.js";
import { graphDetailCodePreSx } from "../graphNodeDetailSectionSx.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   compact: boolean,
 *   rawOpen: boolean,
 *   onRawOpenChange: (next: boolean) => void,
 * }} props
 */
export default function GraphRawPayloadSection({ tk, t, selectedNode, compact, rawOpen, onRawOpenChange }) {
  return (
    <Box sx={{ mt: 1.5 }}>
      <CursorSmallButton type="button" onClick={() => onRawOpenChange(!rawOpen)} sx={{ mb: 0.5 }}>
        {rawOpen ? t("graph.detailPanel.hideAdvanced") : t("graph.detailPanel.showAdvanced")}
      </CursorSmallButton>
      {rawOpen ? (
        <Typography component="pre" sx={graphDetailCodePreSx(tk, compact)}>
          {JSON.stringify(selectedNode.raw && typeof selectedNode.raw === "object" ? selectedNode.raw : {}, null, 2)}
        </Typography>
      ) : null}
    </Box>
  );
}
