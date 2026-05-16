import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * Unified task card shell (extraction / chat / vision / embeddings).
 *
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   cardSx: object,
 *   title: string,
 *   subtitle?: string | null,
 *   headerExtra?: React.ReactNode,
 *   children: React.ReactNode,
 * }} props
 */
export default function LlmTaskCard({ tk, cardSx, title, subtitle, headerExtra, children }) {
  return (
    <Box
      sx={{
        ...cardSx,
        padding: 2,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
      {subtitle ? (
        <Typography sx={{ marginTop: 0.5, fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.5 }}>
          {subtitle}
        </Typography>
      ) : null}
      {headerExtra ? <Box sx={{ marginTop: 1.25 }}>{headerExtra}</Box> : null}
      <Box sx={{ marginTop: 2, display: "flex", flexDirection: "column", gap: 1.5 }}>{children}</Box>
    </Box>
  );
}
