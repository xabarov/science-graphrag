import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import { useTheme } from "@mui/material/styles";
import { useLocation, Link as RouterLink } from "react-router-dom";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

import { CursorIconButton } from "../../common/index.js";
import { useI18n } from "../../../i18n/useI18n.js";
import { isAdminModeEnabled } from "../adminVisibility.js";
import { useWorkspaceContext } from "../useWorkspaceContext.js";
import { appendWorkspaceQuery } from "../../../utils/workspaceStore.js";
import { getLastWorkId } from "../../../pages/WorkspacePage/utils/workContext.js";
import darkLogo from "../../../assets/logo/dark-logo.png";
import lightLogo from "../../../assets/logo/light-logo.png";

const STORAGE_KEY = "sidebarExpanded";

function _readExpanded() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

function itemActive(location, to) {
  const path = String(to || "").split("?")[0] || "";
  return location.pathname === path;
}

export default function Drawer({ onNavigate }) {
  const { t } = useI18n();
  const theme = useTheme();
  const [expanded, setExpanded] = useState(_readExpanded());
  const location = useLocation();
  const adminModeEnabled = isAdminModeEnabled();
  const { activeWorkspaceId, getLastWorkspaceHref } = useWorkspaceContext();
  const logoSrc = theme.palette.mode === "light" ? lightLogo : darkLogo;

  const userMenu = useMemo(() => {
    const wid = activeWorkspaceId || "";
    const sp = new URLSearchParams(location.search || "");
    const workFromUrl = sp.get("work_id") || "";
    const readerWorkId = (workFromUrl || getLastWorkId()).trim();
    const readerHref = readerWorkId
      ? appendWorkspaceQuery(`/reader?work_id=${encodeURIComponent(readerWorkId)}`, wid)
      : "";

    const base = [
      { to: getLastWorkspaceHref(), label: t("shell.drawer.workspace"), icon: <FolderOpenOutlinedIcon /> },
    ];
    if (readerHref) {
      base.push({
        to: readerHref,
        label: t("shell.drawer.reader"),
        icon: <MenuBookOutlinedIcon />,
      });
    }
    base.push(
      { to: appendWorkspaceQuery("/graph", wid), label: t("shell.drawer.graph"), icon: <AccountTreeOutlinedIcon /> },
      { to: appendWorkspaceQuery("/chat", wid), label: t("shell.drawer.chat"), icon: <ChatBubbleOutlineOutlinedIcon /> },
      { to: appendWorkspaceQuery("/evidence", wid), label: t("shell.drawer.evidence"), icon: <FactCheckOutlinedIcon /> },
    );
    return base;
  }, [t, activeWorkspaceId, getLastWorkspaceHref, location.search]);

  const adminMenu = useMemo(
    () =>
      adminModeEnabled
        ? [
            { to: "/admin", label: t("shell.drawer.admin"), icon: <AdminPanelSettingsOutlinedIcon /> },
            { to: "/admin/benchmarks", label: t("shell.drawer.benchmarks"), icon: <ScienceOutlinedIcon /> },
            { to: "/admin/settings", label: t("shell.drawer.settings"), icon: <SettingsOutlinedIcon /> },
          ]
        : [],
    [adminModeEnabled, t],
  );

  function toggleExpanded() {
    const next = !expanded;
    setExpanded(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, String(next));
    } catch {
      // ignore
    }
  }

  function renderNavItem(item) {
    const active = itemActive(location, item.to);
    const content = (
      <Box
        component={RouterLink}
        to={item.to}
        aria-label={expanded ? undefined : item.label}
        onClick={() => onNavigate?.()}
        sx={{
          display: "flex",
          alignItems: "center",
          gap: expanded ? 1.2 : 0,
          padding: expanded ? "10px 12px" : "10px 0",
          borderRadius: 2,
          textDecoration: "none",
          color: "rgba(255,255,255,0.9)",
          background: active ? "rgba(99, 102, 241, 0.15)" : "transparent",
          "&:hover": { background: "rgba(255, 255, 255, 0.04)" },
        }}
      >
        <Box sx={{ fontSize: "1.4rem", display: "flex", alignItems: "center" }}>{item.icon}</Box>
        {expanded && <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{item.label}</Typography>}
      </Box>
    );

    if (expanded) return <Box key={item.to}>{content}</Box>;
    return (
      <Tooltip key={item.to} title={item.label} placement="right">
        <Box>{content}</Box>
      </Tooltip>
    );
  }

  return (
    <Box
      sx={{
        width: expanded ? 280 : 70,
        backgroundColor: "#141414",
        borderRight: "1px solid rgba(255, 255, 255, 0.08)",
        alignSelf: "stretch",
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflowY: "auto",
      }}
    >
      <Box sx={{ padding: expanded ? 2 : 1.5 }}>
        {expanded ? (
          <Box
            component="img"
            src={logoSrc}
            alt={t("shell.drawer.brand")}
            sx={{
              display: "block",
              width: "100%",
              maxWidth: 214,
              height: "auto",
            }}
          />
        ) : (
          <Tooltip title={t("shell.drawer.brand")}>
            <Box
              component="img"
              src={logoSrc}
              alt={t("shell.drawer.brand")}
              sx={{
                display: "block",
                width: 32,
                height: 32,
                objectFit: "contain",
                objectPosition: "left center",
              }}
            />
          </Tooltip>
        )}
      </Box>

      <Box sx={{ padding: expanded ? 1 : 1 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>{userMenu.map(renderNavItem)}</Box>

        {adminMenu.length > 0 ? <Divider sx={{ my: 1.5, borderColor: "rgba(255,255,255,0.08)" }} /> : null}

        {expanded && adminMenu.length > 0 ? (
          <Typography
            sx={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
              color: "rgba(255,255,255,0.28)",
              px: 1.5,
              mb: 0.5,
            }}
          >
            {t("shell.drawer.operations")}
          </Typography>
        ) : null}

        {adminMenu.length > 0 ? <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>{adminMenu.map(renderNavItem)}</Box> : null}
      </Box>

      <Box sx={{ flex: 1 }} />

      <Box sx={{ padding: expanded ? 2 : 1, position: "absolute", bottom: 12, right: expanded ? 12 : 6 }}>
        <CursorIconButton onClick={toggleExpanded} aria-label={t("shell.drawer.toggleSidebar")}>
          <Box sx={{ transform: expanded ? "none" : "rotate(180deg)" }}>{"<"}</Box>
        </CursorIconButton>
      </Box>
    </Box>
  );
}
