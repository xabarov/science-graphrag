import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../../common/index.js";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   handleFitAll: () => void,
 *   handleResetZoom: () => void,
 *   handleCenterSelection: () => void,
 *   canCenter: boolean,
 *   showMinimap: boolean,
 *   setShowMinimap: import("react").Dispatch<import("react").SetStateAction<boolean>>,
 * }} props
 */
export default function GraphFlowToolbar({
  tk,
  handleFitAll,
  handleResetZoom,
  handleCenterSelection,
  canCenter,
  showMinimap,
  setShowMinimap,
}) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, px: 1.5, pt: 1, pb: 0.5, flexShrink: 0 }}>
      <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, flex: "1 1 140px" }}>
        Wheel zooms · drag to pan · click node or edge · Escape clears selection (focus panel first). Same URL selection as
        Canvas.
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
        <CursorSmallButton type="button" onClick={handleFitAll}>
          Fit
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={handleResetZoom}>
          Reset zoom
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={handleCenterSelection} disabled={!canCenter}>
          Center on selected
        </CursorSmallButton>
        <CursorSmallButton type="button" onClick={() => setShowMinimap((v) => !v)} aria-pressed={showMinimap}>
          {showMinimap ? "Hide" : "Show"} minimap
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
