import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import PageHeader from "../components/layout/PageHeader.jsx";
import { CursorPrimaryButton, CursorSmallButton } from "../components/common/index.js";
import { isAdminModeEnabled } from "../components/layout/adminVisibility.js";
import { getContinueWorkspaceTarget } from "./HomePage/homeState.js";

export default function NotFoundPage() {
  const continueTarget = useMemo(() => getContinueWorkspaceTarget(), []);
  const adminModeEnabled = useMemo(() => isAdminModeEnabled(), []);

  return (
    <Box sx={{ p: 2, maxWidth: 960 }}>
      <PageHeader
        eyebrow="Recovery"
        title="Page not found"
        description="This route does not exist or is no longer available. Choose a safe next step to return to the main research or admin flow."
      />

      <Box
        sx={{
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          p: 2,
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>Recommended next actions</Typography>
        <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.55, maxWidth: 700 }}>
          Return to the main entry surfaces, reopen the corpus, or continue the last saved workspace if you were in the middle of a research session.
        </Typography>
        <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CursorPrimaryButton component={Link} to="/" sx={{ textDecoration: "none" }}>
            Go home
          </CursorPrimaryButton>
          <CursorSmallButton component={Link} to="/corpus" sx={{ textDecoration: "none" }}>
            Open corpus
          </CursorSmallButton>
          {continueTarget ? (
            <CursorSmallButton component={Link} to={continueTarget.path} sx={{ textDecoration: "none" }}>
              Continue workspace
            </CursorSmallButton>
          ) : null}
          {adminModeEnabled ? (
            <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
              Open admin
            </CursorSmallButton>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
