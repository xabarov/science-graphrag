import React, { useState } from "react";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import MoreVertOutlinedIcon from "@mui/icons-material/MoreVertOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";

import { CursorIconAction } from "../../common/index.js";
import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { AgentAssistantTurnShell } from "../agent/AgentAssistantTurnShell.jsx";
import MarkdownView from "../markdown/MarkdownView.jsx";
import ChatUserBubble from "./ChatUserBubble.jsx";

/**
 * One completed turn in the ask thread (user bubble + assistant body + actions).
 */
export default function ChatHistoryTurn({
  entry,
  tk,
  t,
  chatDetailLevel = "simple",
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  workspaceId,
  restartDisabled,
  deleteDisabled,
  onRestartFromTurn,
  onCopyAssistantEntry,
  onOpenMetadata,
  onConfirmDelete,
}) {
  const [moreAnchor, setMoreAnchor] = useState(null);

  return (
    <Box
      sx={{
        mb: 2.25,
        "& .turn-actions": {
          opacity: 0,
          transform: "translateY(-2px)",
          transition: "opacity 0.15s ease, transform 0.15s ease",
        },
        "&:hover .turn-actions, &:focus-within .turn-actions": {
          opacity: 1,
          transform: "translateY(0)",
        },
        "@media (hover: none)": {
          "& .turn-actions": { opacity: 1, transform: "none" },
        },
      }}
    >
      <ChatUserBubble text={entry.query} />
      <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
        <Box sx={{ position: "relative", width: "100%", maxWidth: "min(880px, 100%)" }}>
          {entry.details && typeof entry.details === "object" ? (
            <AgentAssistantTurnShell sx={{ mt: 1 }}>
              <AskAnswerPanel
                t={t}
                normalized={entry.details}
                locked={locked}
                inWorkspace={inWorkspace}
                workId={entry.workId || workId}
                workspaceWorkId={workspaceWorkId}
                workspaceId={workspaceId}
                retrievalMode="agent"
                agentToolTrace={Array.isArray(entry.details?.agent_tool_trace) ? entry.details.agent_tool_trace : []}
                retrievalJsonOpen={false}
                onToggleRetrievalJson={() => {}}
                streamEvents={Array.isArray(entry.details?.stream_events) ? entry.details.stream_events : []}
                isRunActive={false}
                chatDetailLevel={chatDetailLevel}
              />
            </AgentAssistantTurnShell>
          ) : (
            <AgentAssistantTurnShell sx={{ mt: 1 }}>
              {String(entry.answer || "").trim() ? (
                <Box
                  sx={{
                    "& .reader-markdown": {
                      fontSize: "0.8125rem",
                      lineHeight: 1.6,
                    },
                    "& .reader-markdown p:last-of-type": {
                      mb: 0,
                    },
                  }}
                >
                  <MarkdownView markdown={String(entry.answer)} />
                </Box>
              ) : (
                <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap" }}>—</Typography>
              )}
            </AgentAssistantTurnShell>
          )}
          <Box className="turn-actions" sx={{ mt: 0.6, display: "flex", alignItems: "center", gap: 0.35 }}>
            <CursorIconAction
              type="button"
              disabled={restartDisabled}
              aria-label={t("chat.thread.actions.retryAria")}
              title={t("chat.thread.actions.retryAria")}
              onClick={() => void onRestartFromTurn?.(entry.id)}
            >
              <ReplayOutlinedIcon sx={{ fontSize: "1rem" }} />
            </CursorIconAction>
            <CursorIconAction
              type="button"
              aria-label={t("chat.thread.actions.copyAria")}
              title={t("chat.thread.actions.copyAria")}
              onClick={() => void onCopyAssistantEntry?.(entry)}
            >
              <ContentCopyOutlinedIcon sx={{ fontSize: "1rem" }} />
            </CursorIconAction>
            <IconButton
              type="button"
              size="small"
              aria-label={t("chat.thread.actions.moreTurnActionsAria")}
              aria-haspopup="true"
              aria-expanded={Boolean(moreAnchor)}
              title={t("chat.thread.actions.moreTurnActionsAria")}
              onClick={(e) => setMoreAnchor(e.currentTarget)}
              sx={{
                color: tk.text.muted,
                p: 0.35,
                "&:hover": { backgroundColor: tk.control.navItemHoverBg },
              }}
            >
              <MoreVertOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </IconButton>
            <Menu
              anchorEl={moreAnchor}
              open={Boolean(moreAnchor)}
              onClose={() => setMoreAnchor(null)}
              slotProps={{
                paper: {
                  sx: {
                    backgroundColor: tk.surface.panel,
                    border: `1px solid ${tk.border.default}`,
                    borderRadius: "6px",
                  },
                },
              }}
            >
              <MenuItem
                onClick={() => {
                  setMoreAnchor(null);
                  onOpenMetadata(entry);
                }}
              >
                {t("chat.thread.actions.menuMetadata")}
              </MenuItem>
              <MenuItem
                disabled={deleteDisabled}
                onClick={() => {
                  setMoreAnchor(null);
                  void onConfirmDelete(entry.id);
                }}
              >
                {t("chat.thread.actions.menuDelete")}
              </MenuItem>
            </Menu>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
