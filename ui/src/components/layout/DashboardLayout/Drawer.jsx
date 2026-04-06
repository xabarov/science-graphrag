import React, { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import { useLocation, Link as RouterLink } from "react-router-dom";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import WorkspacesOutlinedIcon from "@mui/icons-material/WorkspacesOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import QuestionAnswerOutlinedIcon from "@mui/icons-material/QuestionAnswerOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";

import { CursorIconButton } from "../../common/index.js";

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

export default function Drawer({ onNavigate }) {
  const [expanded, setExpanded] = useState(_readExpanded());
  const location = useLocation();

  const menu = useMemo(
    () => [
      { to: "/workspace", label: "Workspace", icon: <WorkspacesOutlinedIcon /> },
      { to: "/reader", label: "Reader", icon: <MenuBookOutlinedIcon /> },
      { to: "/graph", label: "Graph", icon: <AccountTreeOutlinedIcon /> },
      { to: "/ask", label: "Ask", icon: <QuestionAnswerOutlinedIcon /> },
      { to: "/evidence", label: "Evidence", icon: <FactCheckOutlinedIcon /> },
      { to: "/benchmark", label: "Benchmarks", icon: <ScienceOutlinedIcon /> },
    ],
    [],
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
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {menu.map((item) => {
            const active = location.pathname === item.to;
            const content = (
              <Box
                component={RouterLink}
                to={item.to}
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
                <Box sx={{ fontSize: "1.4rem", display: "flex", alignItems: "center" }}>
                  {item.icon}
                </Box>
                {expanded && (
                  <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{item.label}</Typography>
                )}
              </Box>
            );

            if (expanded) return <Box key={item.to}>{content}</Box>;
            return (
              <Tooltip key={item.to} title={item.label} placement="right">
                <Box>{content}</Box>
              </Tooltip>
            );
          })}
        </Box>
      </Box>

      <Box sx={{ flex: 1 }} />

      <Box sx={{ padding: expanded ? 2 : 1, position: "absolute", bottom: 12, right: expanded ? 12 : 6 }}>
        <CursorIconButton onClick={toggleExpanded} aria-label="toggle sidebar">
          <Box sx={{ transform: expanded ? "rotate(180deg)" : "none" }}>{"<"}</Box>
        </CursorIconButton>
      </Box>
    </Box>
  );
}
