import React from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

export default function GraphDebugInspector({ visible, payload, maxHeight = 220 }) {
  const tk = useTheme().appTokens;
  return (
    <Collapse in={visible}>
      <Box sx={{ p: 1.25, borderRadius: "6px", border: `1px solid ${tk.border.default}`, backgroundColor: tk.surface.code }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.75, color: tk.text.primary }}>Diagnostics JSON</Typography>
        <Typography
          component="pre"
          sx={{
            m: 0,
            fontSize: "0.75rem",
            color: tk.text.secondary,
            overflow: "auto",
            maxHeight,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {JSON.stringify(payload, null, 2)}
        </Typography>
      </Box>
    </Collapse>
  );
}
