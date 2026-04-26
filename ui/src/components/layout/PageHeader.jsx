import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/**
 * Compact top-level page header for main application surfaces.
 * @param {{
 *   eyebrow?: string,
 *   title: string,
 *   description?: React.ReactNode,
 *   actions?: React.ReactNode,
 *   compact?: boolean,
 * }} props
 */
export default function PageHeader({ eyebrow = "", title, description = "", actions = null, compact = false }) {
  return (
    <Box
      sx={{
        mb: compact ? 0 : 2.5,
        pb: compact ? 0 : 1.5,
        borderBottom: compact ? "none" : "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        flexWrap: "wrap",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: compact ? 1 : 1.5,
      }}
    >
      <Box sx={{ minWidth: 0, flex: 1 }}>
        {eyebrow ? (
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)", mb: 0.5 }}>{eyebrow}</Typography>
        ) : null}
        <Typography sx={{ fontWeight: 600, color: "rgba(255,255,255,0.92)" }}>{title}</Typography>
        {description ? (
          <Typography component="div" sx={{ mt: 0.65, fontSize: "0.875rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.55 }}>
            {description}
          </Typography>
        ) : null}
      </Box>
      {actions ? <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>{actions}</Box> : null}
    </Box>
  );
}
