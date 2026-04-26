import React from "react";
import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";

import { CursorIconAction } from "../common/index.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   sessionList: Array<{ id: string, title: string, updatedAt?: string, entries?: unknown[] }>,
 *   activeSessionId: string | null,
 *   onActiveSessionChange: (id: string) => void,
 *   onNewSession: () => void,
 *   sx?: object,
 * }} props
 */
export function ChatSessionSidebar({ t, sessionList, activeSessionId, onActiveSessionChange, onNewSession, sx }) {
  return (
    <Box
      sx={{
        width: { xs: "100%", md: 260 },
        flexShrink: 0,
        minHeight: 0,
        height: { md: "100%" },
        display: "flex",
        flexDirection: "column",
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.06)",
        backgroundColor: "rgba(18,18,18,0.65)",
        overflow: "hidden",
        ...sx,
      }}
    >
      <Box sx={{ p: 1.1, borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1, flexShrink: 0 }}>
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: "rgba(255,255,255,0.78)" }}>{t("chat.sidebar.title")}</Typography>
        <CursorIconAction type="button" aria-label={t("chat.sidebar.newChatAria")} title={t("chat.sidebar.newChatAria")} onClick={onNewSession}>
          <AddCommentOutlinedIcon sx={{ fontSize: "1.15rem" }} />
        </CursorIconAction>
      </Box>
      <List dense disablePadding sx={{ flex: 1, overflowY: "auto", py: 0.5, minHeight: 0 }}>
        {sessionList.length === 0 ? (
          <Box sx={{ px: 1.5, py: 2 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.38)" }}>{t("chat.sidebar.empty")}</Typography>
          </Box>
        ) : (
          sessionList.map((s) => (
            <ListItemButton
              key={s.id}
              selected={s.id === activeSessionId}
              onClick={() => onActiveSessionChange(s.id)}
              sx={{
                alignItems: "flex-start",
                py: 1,
                px: 1.15,
                "&.Mui-selected": { backgroundColor: "rgba(99,102,241,0.08)" },
                "&:hover": { backgroundColor: "rgba(255,255,255,0.03)" },
              }}
            >
              <ListItemText
                primary={s.title}
                secondary={Array.isArray(s.entries) && s.entries[0]?.query ? String(s.entries[0].query) : ""}
                primaryTypographyProps={{ noWrap: true, sx: { fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" } }}
                secondaryTypographyProps={{ noWrap: true, sx: { fontSize: "0.68rem", color: "rgba(255,255,255,0.36)", mt: 0.25 } }}
              />
            </ListItemButton>
          ))
        )}
      </List>
    </Box>
  );
}
