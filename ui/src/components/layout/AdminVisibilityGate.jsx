import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";

export default function AdminVisibilityGate() {
  return (
    <Box
      sx={{
        maxWidth: 760,
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)" }}>Admin surface is unavailable</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.55 }}>
        This environment is currently running in research-only mode. Return to Workspaces or continue a workspace session without exposing operational tools.
      </Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorPrimaryButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          Go home
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          Workspaces
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
          Workspace
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
