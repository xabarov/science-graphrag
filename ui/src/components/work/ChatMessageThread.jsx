import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";

import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { AgentAssistantTurnShell } from "./AgentAssistantTurnShell.jsx";
import { AgentRunHeader } from "./AgentRunHeader.jsx";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

function ChatUserBubble({ text }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1.5 }}>
      <Box
        sx={{
          maxWidth: "min(720px, 92%)",
          px: 1.25,
          py: 1,
          borderRadius: "6px",
          backgroundColor: "rgba(99,102,241,0.12)",
          border: "1px solid rgba(99,102,241,0.22)",
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", whiteSpace: "pre-wrap" }}>{text}</Typography>
      </Box>
    </Box>
  );
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   history: Array<{
 *     id: string,
 *     query: string,
 *     workId?: string,
 *     answer?: string,
 *     details?: Record<string, unknown> | null,
 *   }>,
 *   pendingUserQuery: string,
 *   isLoading: boolean,
 *   streamEvents: unknown[],
 *   liveNormalized: unknown | null,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   workspaceWorkId: string | null,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   starterPromptKeys?: string[],
 *   onStarterPrompt?: (text: string) => void,
 * }} props
 */
export function ChatMessageThread({
  t,
  history,
  pendingUserQuery,
  isLoading,
  streamEvents,
  liveNormalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  starterPromptKeys = [],
  onStarterPrompt,
}) {
  const chronological = useMemo(() => [...history].reverse(), [history]);
  const hasThreadContent = chronological.length > 0 || Boolean(pendingUserQuery);
  const showEmptyState = !hasThreadContent;

  const containerRef = useRef(null);
  const endRef = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);

  const updateStickFromScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    setStickToBottom(dist < SCROLL_BOTTOM_THRESHOLD_PX);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    el.addEventListener("scroll", updateStickFromScroll, { passive: true });
    return () => el.removeEventListener("scroll", updateStickFromScroll);
  }, [updateStickFromScroll]);

  const scrollToBottom = useCallback((behavior = "auto") => {
    endRef.current?.scrollIntoView({ block: "end", behavior });
  }, []);

  useLayoutEffect(() => {
    if (pendingUserQuery) {
      scrollToBottom("auto");
      return;
    }
    if (!stickToBottom) return;
    scrollToBottom("auto");
  }, [stickToBottom, scrollToBottom, chronological.length, pendingUserQuery, isLoading, liveNormalized, streamEvents]);

  const showJump = hasThreadContent && !stickToBottom;

  return (
    <Box
      ref={containerRef}
      sx={{
        flex: 1,
        minHeight: 0,
        overflowY: showEmptyState ? "hidden" : "auto",
        pr: 0.5,
        display: "flex",
        flexDirection: "column",
        gap: 0,
        position: "relative",
        justifyContent: showEmptyState ? "flex-end" : "flex-start",
        alignItems: showEmptyState ? "center" : "stretch",
      }}
    >
      {showEmptyState ? (
        <Box
          sx={{
            pb: 1.25,
            width: "100%",
            maxWidth: "min(920px, 100%)",
            mx: "auto",
          }}
        >
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: "rgba(255,255,255,0.82)", mb: 0.5 }}>{t("chat.thread.emptyTitle")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.48)", mb: 1.25, lineHeight: 1.45 }}>{t("chat.thread.emptySubtitle")}</Typography>
          {starterPromptKeys.length > 0 && onStarterPrompt ? (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
              {starterPromptKeys.map((key) => (
                <Chip
                  key={key}
                  size="small"
                  label={t(key)}
                  onClick={() => onStarterPrompt(t(key))}
                  sx={{
                    height: 26,
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    color: "rgba(255,255,255,0.78)",
                    fontSize: "0.75rem",
                    maxWidth: "100%",
                    "& .MuiChip-label": { px: 1, whiteSpace: "normal", textAlign: "left" },
                    "&:hover": { backgroundColor: "rgba(99,102,241,0.1)", borderColor: "rgba(99,102,241,0.25)" },
                  }}
                />
              ))}
            </Box>
          ) : null}
        </Box>
      ) : null}

      {chronological.map((entry) => (
        <Box key={entry.id} sx={{ mb: 2.25 }}>
          <ChatUserBubble text={entry.query} />
          <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
            <Box sx={{ width: "100%", maxWidth: "min(880px, 100%)" }}>
              {entry.details && typeof entry.details === "object" ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AskAnswerPanel
                    t={t}
                    normalized={entry.details}
                    locked={locked}
                    inWorkspace={inWorkspace}
                    workId={entry.workId || workId}
                    workspaceWorkId={workspaceWorkId}
                    retrievalMode="agent"
                    agentToolTrace={
                      Array.isArray(entry.details?.agent_tool_trace) ? entry.details.agent_tool_trace : []
                    }
                    retrievalJsonOpen={false}
                    onToggleRetrievalJson={() => {}}
                    streamEvents={
                      Array.isArray(entry.details?.stream_events) ? entry.details.stream_events : []
                    }
                    isRunActive={false}
                  />
                </AgentAssistantTurnShell>
              ) : (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", whiteSpace: "pre-wrap" }}>{entry.answer || "—"}</Typography>
                </AgentAssistantTurnShell>
              )}
            </Box>
          </Box>
        </Box>
      ))}

      {pendingUserQuery ? (
        <Box sx={{ mb: 2.25 }}>
          <ChatUserBubble text={pendingUserQuery} />
          <Box sx={{ display: "flex", justifyContent: "flex-start", pl: 0.5 }}>
            <Box sx={{ flex: 1, minWidth: 0, maxWidth: "min(880px, 100%)" }}>
              {liveNormalized ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AskAnswerPanel
                    t={t}
                    normalized={liveNormalized}
                    locked={locked}
                    inWorkspace={inWorkspace}
                    workId={workId}
                    workspaceWorkId={workspaceWorkId}
                    retrievalMode="agent"
                    agentToolTrace={agentToolTrace}
                    retrievalJsonOpen={retrievalJsonOpen}
                    onToggleRetrievalJson={onToggleRetrievalJson}
                    streamEvents={streamEvents}
                    isRunActive={isLoading}
                  />
                </AgentAssistantTurnShell>
              ) : isLoading ? (
                <AgentAssistantTurnShell sx={{ mt: 1 }}>
                  <AgentRunHeader
                    t={t}
                    runState="running"
                    answerClass={null}
                    citationCount={0}
                    durationMs={null}
                    streamEventCount={Array.isArray(streamEvents) ? streamEvents.length : 0}
                  />
                  <AgentLiveStatus t={t} streamEvents={streamEvents} isActive />
                </AgentAssistantTurnShell>
              ) : null}
            </Box>
          </Box>
        </Box>
      ) : null}

      {showJump ? (
        <IconButton
          type="button"
          size="small"
          onClick={() => {
            setStickToBottom(true);
            scrollToBottom("smooth");
          }}
          aria-label={t("chat.thread.jumpBottomAria")}
          title={t("chat.thread.jumpBottomAria")}
          sx={{
            position: "absolute",
            right: 4,
            bottom: 8,
            zIndex: 2,
            border: "1px solid rgba(255,255,255,0.12)",
            backgroundColor: "rgba(26,26,26,0.92)",
            color: "rgba(255,255,255,0.75)",
            "&:hover": { backgroundColor: "rgba(99,102,241,0.15)" },
          }}
        >
          <KeyboardArrowDownRoundedIcon sx={{ fontSize: "1.15rem" }} />
        </IconButton>
      ) : null}

      <Box ref={endRef} sx={{ height: 1, flexShrink: 0, width: "100%" }} />
    </Box>
  );
}
