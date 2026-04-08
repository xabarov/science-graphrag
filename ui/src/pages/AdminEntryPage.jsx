import React from "react";
import { Link } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import AdminApiStatusStrip from "./AdminApiStatusStrip.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";

function AdminCard({ title, description, primaryTo, primaryLabel, secondaryTo, secondaryLabel }) {
  return (
    <Box
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: 2,
      }}
    >
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.58)", lineHeight: 1.55 }}>{description}</Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorPrimaryButton component={Link} to={primaryTo} sx={{ textDecoration: "none" }}>
          {primaryLabel}
        </CursorPrimaryButton>
        {secondaryTo ? (
          <CursorSmallButton component={Link} to={secondaryTo} sx={{ textDecoration: "none" }}>
            {secondaryLabel}
          </CursorSmallButton>
        ) : null}
      </Box>
    </Box>
  );
}

export default function AdminEntryPage() {
  return (
    <Box sx={{ p: { xs: 1.5, sm: 0 }, ...mainShellContentSx }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)", mb: 1 }}>API status</Typography>
      <AdminApiStatusStrip />
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 1.5 }}>
        <AdminCard
          title="Benchmarks"
          description="Run benchmark flows, inspect workbench output, compare runs, and review benchmark cases."
          primaryTo="/admin/benchmarks"
          primaryLabel="Open benchmarks"
          secondaryTo="/admin/benchmarks?tab=workbench"
          secondaryLabel="Open workbench"
        />
        <AdminCard
          title="Settings"
          description="Configure runtime and LLM settings with a dedicated settings layout that can grow over time."
          primaryTo="/admin/settings"
          primaryLabel="Open settings"
        />
        <AdminCard
          title="Diagnostics"
          description="Health and catalog probes plus JSON details. Extend with deeper metrics when backend exposes read-only status APIs."
          primaryTo="/admin/diagnostics"
          primaryLabel="Open diagnostics"
        />
      </Box>
    </Box>
  );
}
