import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

/**
 * Outer card for a single assistant turn (aligned with research workspace chat chrome).
 *
 * @param {{ children: React.ReactNode, sx?: object, dense?: boolean }} props
 */
export function AgentAssistantTurnShell({ children, sx = {}, dense = false }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        width: "100%",
        p: dense ? 1.25 : 2,
        borderRadius: "6px",
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        boxSizing: "border-box",
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
