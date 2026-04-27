import React from "react";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";

/**
 * Two-column workspace body: main (papers + dedup) / side (ingest + stats).
 * @param {{ main: React.ReactNode, side: React.ReactNode }} props
 */
export default function WorkspaceLayout({ main, side }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 2fr) minmax(280px, 1fr)" },
        gap: 2,
        alignItems: "stretch",
        minHeight: { xs: "min(72dvh, 720px)", lg: "min(70dvh, 820px)" },
      }}
    >
      <Box
        sx={{
          minWidth: 0,
          order: { xs: 2, lg: 1 },
          display: "flex",
          flexDirection: "column",
          minHeight: 0,
        }}
      >
        {main}
      </Box>
      <Box
        sx={{
          minWidth: 0,
          order: { xs: 1, lg: 2 },
          position: { lg: "sticky" },
          top: { lg: 12 },
          alignSelf: { lg: "start" },
          maxHeight: { lg: "min(calc(100dvh - 120px), 100%)" },
          overflowY: { lg: "auto" },
          p: { lg: 1.5 },
          borderRadius: "6px",
          border: { lg: `1px solid ${tk.border.default}` },
          backgroundColor: { lg: tk.surface.panel },
        }}
      >
        {side}
      </Box>
    </Box>
  );
}
