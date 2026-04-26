import React, { useMemo } from "react";
import Box from "@mui/material/Box";
import { Link, Outlet, useLocation } from "react-router-dom";

import { useI18n } from "../../i18n/useI18n.js";
import PageHeader from "./PageHeader.jsx";
import { CursorSmallButton } from "../common/index.js";
import { isAdminModeEnabled } from "./adminVisibility.js";

const ADMIN_HEADER_CONFIG = {
  "/admin": {
    eyebrowKey: "shell.adminHeader.operationsSurface",
    titleKey: "shell.adminHeader.adminTitle",
    descriptionKey: "shell.adminHeader.adminDescription",
  },
  "/admin/benchmarks": {
    eyebrowKey: "shell.adminHeader.adminTools",
    titleKey: "shell.adminHeader.benchmarksTitle",
    descriptionKey: "shell.adminHeader.benchmarksDescription",
  },
  "/admin/settings": {
    eyebrowKey: "shell.adminHeader.adminTools",
    titleKey: "shell.adminHeader.settingsTitle",
    descriptionKey: "shell.adminHeader.settingsDescription",
  },
  "/admin/diagnostics": {
    eyebrowKey: "shell.adminHeader.adminTools",
    titleKey: "shell.adminHeader.diagnosticsTitle",
    descriptionKey: "shell.adminHeader.diagnosticsDescription",
  },
};

export default function AdminLayout() {
  const { t } = useI18n();
  const location = useLocation();
  const header = useMemo(() => {
    const cfg = ADMIN_HEADER_CONFIG[location.pathname] || ADMIN_HEADER_CONFIG["/admin"];
    return {
      eyebrow: t(cfg.eyebrowKey),
      title: t(cfg.titleKey),
      description: t(cfg.descriptionKey),
    };
  }, [location.pathname, t]);
  const showAdminHubAction = location.pathname !== "/admin";
  const adminModeEnabled = isAdminModeEnabled();

  return (
    <Box sx={{ p: 2 }}>
      <PageHeader
        eyebrow={header.eyebrow}
        title={header.title}
        description={header.description}
        actions={
          <>
            {showAdminHubAction ? (
              <CursorSmallButton component={Link} to="/admin" sx={{ textDecoration: "none" }}>
                {t("shell.adminHeader.adminHub")}
              </CursorSmallButton>
            ) : null}
            {adminModeEnabled ? (
              <CursorSmallButton component={Link} to="/admin/benchmarks" sx={{ textDecoration: "none" }}>
                {t("shell.adminHeader.benchmarks")}
              </CursorSmallButton>
            ) : null}
            <CursorSmallButton component={Link} to="/" sx={{ textDecoration: "none" }}>
              {t("shell.adminHeader.home")}
            </CursorSmallButton>
          </>
        }
      />
      <Outlet />
    </Box>
  );
}
