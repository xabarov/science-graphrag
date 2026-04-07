import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

/** Placeholder admin route for future diagnostics tooling. */
export default function DiagnosticsPage() {
  return (
    <Box sx={{ p: 2, maxWidth: 720 }}>
      <Typography sx={{ fontWeight: 600, mb: 1, color: "rgba(255,255,255,0.9)" }}>Diagnostics</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
        Reserved for operational diagnostics. Not part of UI/UX wave 1 scope — coming in a later iteration.
      </Typography>
    </Box>
  );
}
