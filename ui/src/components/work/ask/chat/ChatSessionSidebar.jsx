import React, { useMemo } from "react";
import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorIconAction } from "../../../common/index.js";

/** @param {{ entries?: unknown[] }} session */
function sessionListSecondaryLine(session) {
  const e0 = Array.isArray(session?.entries) ? session.entries[0] : null;
  const rm = e0?.details?.run_metadata;
  const brief = rm && typeof rm === "object" && typeof rm.brief === "string" ? rm.brief.trim() : "";
  if (brief) return brief.length > 120 ? `${brief.slice(0, 117)}…` : brief;
  return e0?.query ? String(e0.query) : "";
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   sessionList: Array<{ id: string, title: string, updatedAt?: string, entries?: unknown[] }>,
 *   activeSessionId: string | null,
 *   onActiveSessionChange: (id: string) => void,
 *   onNewSession: () => void,
 *   onDeleteSessionRequest?: (session: { id: string, title: string, updatedAt?: string, entries?: unknown[] }) => void | Promise<void>,
 *   sx?: object,
 * }} props
 */
export function ChatSessionSidebar({
  t,
  sessionList,
  activeSessionId,
  onActiveSessionChange,
  onNewSession,
  onDeleteSessionRequest,
  sx,
}) {
  const tk = useTheme().appTokens;
  const rootSx = useMemo(
    () => ({
      width: { xs: "100%", md: 220 },
      flexShrink: 0,
      minHeight: 0,
      height: { md: "100%" },
      display: "flex",
      flexDirection: "column",
      borderRadius: "6px",
      border: `1px solid ${tk.border.default}`,
      backgroundColor: tk.surface.panelAlt,
      overflow: "hidden",
      ...sx,
    }),
    [tk, sx],
  );

  return (
    <Box sx={rootSx}>
      <Box
        sx={{
          p: { xs: 0.75, sm: 0.9, md: 1.1 },
          borderBottom: `1px solid ${tk.border.default}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          flexShrink: 0,
        }}
      >
        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", color: tk.text.primary }}>{t("chat.sidebar.title")}</Typography>
        <CursorIconAction type="button" aria-label={t("chat.sidebar.newChatAria")} title={t("chat.sidebar.newChatAria")} onClick={onNewSession}>
          <AddCommentOutlinedIcon sx={{ fontSize: "1.15rem" }} />
        </CursorIconAction>
      </Box>
      <List dense disablePadding sx={{ flex: 1, overflowY: "auto", py: 0.5, minHeight: 0 }}>
        {sessionList.length === 0 ? (
          <Box sx={{ px: { xs: 1, md: 1.5 }, py: { xs: 1.25, md: 2 } }}>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.faint }}>{t("chat.sidebar.empty")}</Typography>
          </Box>
        ) : (
          sessionList.map((s) => (
            <ListItem
              key={s.id}
              disablePadding
              secondaryAction={
                onDeleteSessionRequest ? (
                  <Box
                    component="span"
                    sx={{ display: "inline-flex", alignItems: "center", pr: 0.5 }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <CursorIconAction
                      type="button"
                      aria-label={t("chat.sidebar.deleteAria")}
                      title={t("chat.sidebar.deleteAria")}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteSessionRequest(s);
                      }}
                    >
                      <DeleteOutlineOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                    </CursorIconAction>
                  </Box>
                ) : null
              }
              sx={{
                alignItems: "stretch",
                borderBottom: `1px solid ${tk.border.default}`,
                "&:last-of-type": { borderBottom: "none" },
              }}
            >
              <ListItemButton
                selected={s.id === activeSessionId}
                onClick={() => onActiveSessionChange(s.id)}
                sx={{
                  alignItems: "flex-start",
                  py: { xs: 0.65, md: 1 },
                  px: { xs: 0.75, sm: 0.95, md: 1.15 },
                  pr: onDeleteSessionRequest ? 5 : { xs: 0.75, sm: 0.95, md: 1.15 },
                  "&.Mui-selected": { backgroundColor: tk.accent.softBg },
                  "&.Mui-selected:hover": { backgroundColor: tk.accent.emphasisHoverBg },
                  "&:hover": { backgroundColor: tk.control.navItemHoverBg },
                }}
              >
                <ListItemText
                  primary={s.title}
                  secondary={sessionListSecondaryLine(s)}
                  primaryTypographyProps={{ noWrap: true, sx: { fontSize: "0.8125rem", color: tk.text.primary } }}
                  secondaryTypographyProps={{ noWrap: true, sx: { fontSize: "0.68rem", color: tk.text.faint, mt: 0.25 } }}
                />
              </ListItemButton>
            </ListItem>
          ))
        )}
      </List>
    </Box>
  );
}
