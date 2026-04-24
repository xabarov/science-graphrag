import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import { CursorPrimaryButton, CursorSmallButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";

export default function AdminVisibilityGate() {
  const { t } = useI18n();
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
      <Typography sx={{ fontWeight: 600, fontSize: "0.9375rem", color: "rgba(255,255,255,0.9)" }}>{t("adminGate.title")}</Typography>
      <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.55 }}>
        {t("adminGate.body")}
      </Typography>
      <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
        <CursorPrimaryButton component={Link} to="/" sx={{ textDecoration: "none" }}>
          {t("adminGate.goHome")}
        </CursorPrimaryButton>
        <CursorSmallButton component={Link} to="/workspaces" sx={{ textDecoration: "none" }}>
          {t("adminGate.workspaces")}
        </CursorSmallButton>
        <CursorSmallButton component={Link} to="/workspace" sx={{ textDecoration: "none" }}>
          {t("adminGate.workspace")}
        </CursorSmallButton>
      </Box>
    </Box>
  );
}
