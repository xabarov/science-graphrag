import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

/**
 * Fallback panel for snapshot sections without a dedicated settings UI.
 *
 * @param {{ title: string, description: string }} props
 */
export function PlaceholderSettingsSection({ title, description }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      sx={{
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        borderRadius: 1.5,
        padding: 2.5,
      }}
    >
      <Typography sx={{ fontSize: "0.875rem", fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
      <Typography sx={{ marginTop: 1, fontSize: "0.8125rem", color: tk.text.secondary, lineHeight: 1.6 }}>
        {description}
      </Typography>
    </Box>
  );
}
