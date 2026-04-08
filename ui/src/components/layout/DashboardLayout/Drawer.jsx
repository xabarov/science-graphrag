import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import { useLocation, Link as RouterLink } from "react-router-dom";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import HomeOutlinedIcon from "@mui/icons-material/HomeOutlined";
import WorkspacesOutlinedIcon from "@mui/icons-material/WorkspacesOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";

import { CursorIconButton } from "../../common/index.js";
import { isAdminModeEnabled } from "../adminVisibility.js";

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
  return location.pathname === to;
}

export default function Drawer({ onNavigate }) {
  const [expanded, setExpanded] = useState(_readExpanded());
  const location = useLocation();
  const adminModeEnabled = isAdminModeEnabled();

  const userMenu = useMemo(
    () => [
      { to: "/", label: "Home", icon: <HomeOutlinedIcon /> },
      { to: "/corpus", label: "Corpus", icon: <FolderOpenOutlinedIcon /> },
      { to: "/workspace", label: "Workspace", icon: <WorkspacesOutlinedIcon /> },
    ],
    [],
  );

  const directEntryMenu = useMemo(
    () => [
      { to: "/reader", label: "Reader", icon: <MenuBookOutlinedIcon /> },
      { to: "/graph", label: "Graph", icon: <AccountTreeOutlinedIcon /> },
      { to: "/ask", label: "Ask", icon: <QuestionAnswerOutlinedIcon /> },
      { to: "/evidence", label: "Evidence", icon: <FactCheckOutlinedIcon /> },
    ],
    [],
  );

  const adminMenu = useMemo(
    () =>
      adminModeEnabled
        ? [
            { to: "/admin", label: "Admin", icon: <ScienceOutlinedIcon /> },
            { to: "/admin/benchmarks", label: "Benchmarks", icon: <ScienceOutlinedIcon /> },
            { to: "/admin/settings", label: "Settings", icon: <SettingsOutlinedIcon /> },
          ]
        : [],
    [adminModeEnabled],
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
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        position: "relative",
      }}
    >
      <Box sx={{ padding: expanded ? 2 : 1.5 }}>
        {expanded ? (
          <Typography sx={{ fontWeight: 700 }}>science-graphrag</Typography>
        ) : (
          <Tooltip title="science-graphrag">
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <FolderOpenOutlinedIcon />
            </Box>
          </Tooltip>
        )}
      </Box>

      <Box sx={{ padding: expanded ? 1 : 1 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>{userMenu.map(renderNavItem)}</Box>

        {expanded ? (
          <Typography
            sx={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              letterSpacing: "0.02em",
              color: "rgba(255,255,255,0.28)",
              px: 1.5,
              mt: 1.5,
              mb: 0.5,
            }}
          >
            Secondary access
          </Typography>
        ) : null}

        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>{directEntryMenu.map(renderNavItem)}</Box>

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
            Operations
          </Typography>
        ) : null}

        {adminMenu.length > 0 ? <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>{adminMenu.map(renderNavItem)}</Box> : null}
      </Box>

      <Box sx={{ flex: 1 }} />

      <Box sx={{ padding: expanded ? 2 : 1, position: "absolute", bottom: 12, right: expanded ? 12 : 6 }}>
        <CursorIconButton onClick={toggleExpanded} aria-label="toggle sidebar">
          <Box sx={{ transform: expanded ? "none" : "rotate(180deg)" }}>{"<"}</Box>
        </CursorIconButton>
      </Box>
    </Box>
  );
}
