import React from "react";
import FolderOpenOutlinedIcon from "@mui/icons-material/FolderOpenOutlined";
import Box from "@mui/material/Box";
import ListItemButton from "@mui/material/ListItemButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

function shortWorkspaceId(wsId) {
  const s = String(wsId || "").trim();
  if (!s) return "";
  if (s.length <= 14) return s;
  return `${s.slice(0, 8)}…`;
}

function workIdsLen(ws) {
  return Array.isArray(ws.work_ids) ? ws.work_ids.length : 0;
}

/**
 * @param {{ ws: { id: string, name?: string, work_ids?: string[], created_at?: string }, activeWorkspaceId: string | null, onPick: (id: string) => void, t: (k: string, v?: Record<string, string | number>) => string }} props
 */
export default function WorkspaceContextWorkspaceRow({ ws, activeWorkspaceId, onPick, t }) {
  const tk = useTheme().appTokens;
  const name = (ws.name || "").trim();
  const primary = name || shortWorkspaceId(ws.id);
  const showIdSubline = Boolean(name);
  const nWorks = workIdsLen(ws);
  const worksLabel = t("shell.workspaceChip.worksCount", { count: String(nWorks) });

  return (
    <ListItemButton
      title={ws.id}
      selected={ws.id === activeWorkspaceId}
      onClick={() => onPick(ws.id)}
      sx={{
        alignItems: "flex-start",
        py: 1,
        px: 1.25,
        gap: 1,
        borderRadius: 1,
        "&.Mui-selected": {
          backgroundColor: tk.accent.softBg,
        },
        "&.Mui-selected:hover": {
          backgroundColor: tk.accent.emphasisHoverBg,
        },
        "&:hover": {
          backgroundColor: tk.control.navItemHoverBg,
        },
      }}
    >
      <FolderOpenOutlinedIcon sx={{ fontSize: "1.125rem", color: tk.text.muted, mt: 0.125, flexShrink: 0 }} />
      <Box sx={{ minWidth: 0, flex: 1 }}>
        <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, color: tk.text.primary, lineHeight: 1.25 }} noWrap>
          {primary}
        </Typography>
        {showIdSubline ? (
          <Typography
            component="div"
            sx={{
              fontSize: "0.65rem",
              fontFamily: "ui-monospace, monospace",
              color: tk.text.faint,
              mt: 0.25,
            }}
            noWrap
          >
            {shortWorkspaceId(ws.id)}
          </Typography>
        ) : null}
      </Box>
      <Typography
        sx={{
          flexShrink: 0,
          fontSize: "0.6875rem",
          fontWeight: 500,
          color: tk.text.faint,
          mt: 0.125,
          maxWidth: "5.5rem",
          textAlign: "right",
        }}
        noWrap
        title={worksLabel}
      >
        {worksLabel}
      </Typography>
    </ListItemButton>
  );
}
