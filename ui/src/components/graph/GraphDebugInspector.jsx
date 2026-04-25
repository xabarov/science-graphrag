import React from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";

export default function GraphDebugInspector({ visible, payload, maxHeight = 220 }) {
  return (
    <Collapse in={visible}>
      <Box sx={{ p: 1.25, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.75 }}>Diagnostics JSON</Typography>
        <Typography
          component="pre"
          sx={{
            m: 0,
            fontSize: "0.75rem",
            color: "rgba(255,255,255,0.6)",
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
