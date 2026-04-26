import React from "react";
import Box from "@mui/material/Box";

/**
 * Outer card for a single assistant turn (aligned with research workspace chat chrome).
 *
 * @param {{ children: React.ReactNode, sx?: object }} props
 */
export function AgentAssistantTurnShell({ children, sx = {} }) {
  return (
    <Box
      sx={{
        width: "100%",
        p: 2,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        boxSizing: "border-box",
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
