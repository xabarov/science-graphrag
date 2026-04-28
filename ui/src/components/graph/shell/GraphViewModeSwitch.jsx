import React from "react";
import Box from "@mui/material/Box";

import { CursorSmallButton } from "../../common/index.js";

const ACTIVE_SX = {
  backgroundColor: "rgba(99, 102, 241, 0.15)",
  borderColor: "rgba(99, 102, 241, 0.3)",
  color: "rgba(129,140,248,0.92)",
};

export default function GraphViewModeSwitch({ mode, onChange, compact = false }) {
  return (
    <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: compact ? 1 : 1.5, alignItems: "center" }}>
      <CursorSmallButton type="button" onClick={() => onChange("cards")} sx={mode === "cards" ? ACTIVE_SX : {}}>
        Cards
      </CursorSmallButton>
      <CursorSmallButton type="button" onClick={() => onChange("canvas")} sx={mode === "canvas" ? ACTIVE_SX : {}}>
        Graph
      </CursorSmallButton>
      <CursorSmallButton type="button" onClick={() => onChange("flow")} sx={mode === "flow" ? ACTIVE_SX : {}}>
        Flow
      </CursorSmallButton>
    </Box>
  );
}
