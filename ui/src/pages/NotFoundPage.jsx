import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { Link } from "react-router-dom";

import PageHeader from "../components/layout/PageHeader.jsx";
import { mainShellContentSx } from "../components/layout/mainShellContentSx.js";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";

import { CursorIconAction } from "../components/common/index.js";
import { isAdminModeEnabled } from "../components/layout/adminVisibility.js";
import { useI18n } from "../i18n/useI18n.js";
import { getContinueWorkspaceTarget } from "./HomePage/homeState.js";

export default function NotFoundPage() {
  const { t } = useI18n();
  const continueTarget = useMemo(() => getContinueWorkspaceTarget(), []);
  const adminModeEnabled = useMemo(() => isAdminModeEnabled(), []);

  return (
    <Box sx={{ p: 2, ...mainShellContentSx }}>
      <PageHeader
        eyebrow={t("notFound.header.eyebrow")}
        title={t("notFound.header.title")}
        description={t("notFound.header.description")}
      />

      <Box
        sx={{
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          p: 2,
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.9)" }}>
          {t("notFound.actions.title")}
        </Typography>
        <Typography sx={{ mt: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.55, maxWidth: 700 }}>
          {t("notFound.actions.body")}
        </Typography>
        <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          <CursorIconAction component={Link} to="/" title={t("notFound.actions.goHome")}>
            <HomeOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
          <CursorIconAction component={Link} to="/workspaces" title={t("notFound.actions.workspaces")}>
            <FolderOpenOutlinedIcon sx={{ fontSize: "1.1rem" }} />
          </CursorIconAction>
          {continueTarget ? (
            <CursorIconAction component={Link} to={continueTarget.path} title={t("notFound.actions.continueWorkspace")}>
              <HubOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
          ) : null}
          {adminModeEnabled ? (
            <CursorIconAction component={Link} to="/admin" title={t("notFound.actions.openAdmin")}>
              <AdminPanelSettingsOutlinedIcon sx={{ fontSize: "1.1rem" }} />
            </CursorIconAction>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
