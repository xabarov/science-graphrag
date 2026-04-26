import React from "react";
import Box from "@mui/material/Box";

/**
 * Two-column workspace body: main (papers + dedup) / side (ingest + stats).
 * @param {{ main: React.ReactNode, side: React.ReactNode }} props
 */
export default function WorkspaceLayout({ main, side }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 2fr) minmax(280px, 1fr)" },
        gap: 2,
        alignItems: "start",
      }}
    >
      <Box sx={{ minWidth: 0, order: { xs: 2, lg: 1 } }}>{main}</Box>
      <Box
        sx={{
          minWidth: 0,
          order: { xs: 1, lg: 2 },
          position: { lg: "sticky" },
          top: { lg: 12 },
          alignSelf: { lg: "start" },
          maxHeight: { lg: "calc(100vh - 72px)" },
          overflowY: { lg: "auto" },
          p: { lg: 1.5 },
          borderRadius: "6px",
          border: { lg: "1px solid rgba(255,255,255,0.08)" },
          backgroundColor: { lg: "#1a1a1a" },
        }}
      >
        {side}
      </Box>
    </Box>
  );
}
