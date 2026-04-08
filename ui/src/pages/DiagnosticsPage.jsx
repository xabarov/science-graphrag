import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import { CursorSmallButton } from "../components/common/index.js";

export default function DiagnosticsPage() {
  return (
    <Box sx={{ maxWidth: 720 }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>Diagnostics placeholder</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem" }}>
        Reserved for operational diagnostics. This route now exists as part of the admin surface, while the deeper runtime payload and status cards are still scheduled for a later pass.
      </Typography>
      <Box sx={{ mt: 1.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
          Back to admin
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          Home
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
