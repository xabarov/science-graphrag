import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { useFeedback } from "../../feedback/index.js";
import ChatHistoryTurn from "./ChatHistoryTurn.jsx";
import ChatPendingStreamBlock from "./ChatPendingStreamBlock.jsx";
import ChatThreadMetadataDialog from "./ChatThreadMetadataDialog.jsx";
import AskUserQuestionForm from "./AskUserQuestionForm.jsx";
import { SCROLL_BOTTOM_THRESHOLD_PX, extractTurnMetadata } from "./chatThreadMetrics.js";

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   chatDetailLevel?: "simple" | "detailed",
 *   scopeKey: string,
 *   activeSessionId: string | null,
 *   streamingTarget: { scopeKey: string, sessionId: string } | null,
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
 *   workspaceId?: string,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   starterPromptKeys?: string[],
 *   onStarterPrompt?: (text: string) => void,
 *   onRestartFromTurn?: (turnId: string) => void | Promise<void>,
 *   onCopyAssistantEntry?: (entry: unknown) => void | Promise<void>,
 *   onDeleteTurn?: (turnId: string) => void | Promise<void>,
 *   restartDisabled?: boolean,
 *   deleteDisabled?: boolean,
 *   openStructuredQuestion?: { request_id: string, questions: unknown[] } | null,
 *   onStructuredAnswersSubmit?: (payload: { request_id: string, answers: unknown[] }) => void | Promise<void>,
 * }} props
 */
export function ChatMessageThread({
  t,
  chatDetailLevel = "simple",
  scopeKey,
  activeSessionId,
  streamingTarget,
  history,
  pendingUserQuery,
  isLoading,
  streamEvents,
  liveNormalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  workspaceId = "",
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  starterPromptKeys = [],
  onStarterPrompt,
  onRestartFromTurn,
  onCopyAssistantEntry,
  onDeleteTurn,
  restartDisabled = false,
  deleteDisabled = false,
  openStructuredQuestion = null,
  onStructuredAnswersSubmit,
}) {
  const { confirm } = useFeedback();
  const tk = useTheme().appTokens;
  const chronological = useMemo(() => [...history].reverse(), [history]);
  const streamForThisChat = Boolean(
    streamingTarget &&
      streamingTarget.scopeKey === scopeKey &&
      String(streamingTarget.sessionId || "") === String(activeSessionId || ""),
  );
  const hasThreadContent =
    chronological.length > 0 ||
    (Boolean(pendingUserQuery) && streamForThisChat) ||
    (Boolean(liveNormalized) && streamForThisChat);
  const showEmptyState = !hasThreadContent;

  const containerRef = useRef(null);
  const [stickToBottom, setStickToBottom] = useState(true);
  const stickToBottomRef = useRef(true);

  const updateStickFromScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    const stick = dist < SCROLL_BOTTOM_THRESHOLD_PX;
    stickToBottomRef.current = stick;
    setStickToBottom(stick);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    el.addEventListener("scroll", updateStickFromScroll, { passive: true });
    return () => el.removeEventListener("scroll", updateStickFromScroll);
  }, [updateStickFromScroll]);

  const scrollContainerToBottom = useCallback((behavior = "auto") => {
    const el = containerRef.current;
    if (!el) return;
    const top = el.scrollHeight - el.clientHeight;
    if (behavior === "smooth") {
      el.scrollTo({ top, behavior: "smooth" });
    } else {
      el.scrollTop = top;
    }
  }, []);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!stickToBottomRef.current) return;
    scrollContainerToBottom("auto");
  }, [
    scrollContainerToBottom,
    chronological.length,
    pendingUserQuery,
    isLoading,
    liveNormalized,
    streamEvents,
    streamForThisChat,
    openStructuredQuestion,
  ]);

  const showJump = hasThreadContent && !stickToBottom;
  const [metaEntry, setMetaEntry] = useState(null);
  const meta = useMemo(() => extractTurnMetadata(metaEntry), [metaEntry]);

  const handleConfirmDelete = useCallback(
    async (turnId) => {
      const ok = await confirm({
        title: t("chat.thread.deleteTurnDialogTitle"),
        body: t("chat.thread.deleteTurnConfirm"),
        variant: "danger",
        confirmLabel: t("chat.sidebar.deleteConfirmButton"),
        cancelLabel: t("chat.clear.cancel"),
      });
      if (!ok) return;
      void onDeleteTurn?.(turnId);
    },
    [confirm, onDeleteTurn, t],
  );

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
        justifyContent: "flex-start",
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem", color: tk.text.primary, mb: 0.5 }}>{t("chat.thread.emptyTitle")}</Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1.25, lineHeight: 1.45 }}>{t("chat.thread.emptySubtitle")}</Typography>
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
                    border: `1px solid ${tk.border.strong}`,
                    backgroundColor: tk.surface.subtle,
                    color: tk.text.primary,
                    fontSize: "0.75rem",
                    maxWidth: "100%",
                    "& .MuiChip-label": { px: 1, whiteSpace: "normal", textAlign: "left" },
                    "&:hover": { backgroundColor: tk.accent.chipReadyBg, borderColor: tk.accent.softBorder },
                  }}
                />
              ))}
            </Box>
          ) : null}
        </Box>
      ) : null}

      {chronological.map((entry) => (
        <ChatHistoryTurn
          key={entry.id}
          entry={entry}
          tk={tk}
          t={t}
          chatDetailLevel={chatDetailLevel}
          locked={locked}
          inWorkspace={inWorkspace}
          workId={workId}
          workspaceWorkId={workspaceWorkId}
          workspaceId={workspaceId}
          restartDisabled={restartDisabled}
          deleteDisabled={deleteDisabled}
          onRestartFromTurn={onRestartFromTurn}
          onCopyAssistantEntry={onCopyAssistantEntry}
          onOpenMetadata={setMetaEntry}
          onConfirmDelete={handleConfirmDelete}
        />
      ))}

      {pendingUserQuery && streamForThisChat ? (
        <ChatPendingStreamBlock
          t={t}
          chatDetailLevel={chatDetailLevel}
          pendingUserQuery={pendingUserQuery}
          liveNormalized={liveNormalized}
          locked={locked}
          inWorkspace={inWorkspace}
          workId={workId}
          workspaceWorkId={workspaceWorkId}
          workspaceId={workspaceId}
          agentToolTrace={agentToolTrace}
          retrievalJsonOpen={retrievalJsonOpen}
          onToggleRetrievalJson={onToggleRetrievalJson}
          streamEvents={streamEvents}
          isLoading={isLoading}
        />
      ) : null}

      {openStructuredQuestion && !pendingUserQuery && !isLoading ? (
        <Box sx={{ width: "100%", maxWidth: "min(920px, 100%)", mx: "auto", px: { xs: 0.5, sm: 0 } }}>
          <AskUserQuestionForm
            key={String(openStructuredQuestion.request_id || "")}
            t={t}
            envelope={openStructuredQuestion}
            onSubmitAnswers={(p) => void onStructuredAnswersSubmit?.(p)}
            disabled={isLoading}
          />
        </Box>
      ) : null}

      <ChatThreadMetadataDialog open={Boolean(metaEntry)} onClose={() => setMetaEntry(null)} tk={tk} t={t} meta={meta} />

      {showJump ? (
        <IconButton
          type="button"
          size="small"
          onClick={() => {
            stickToBottomRef.current = true;
            setStickToBottom(true);
            scrollContainerToBottom("smooth");
          }}
          aria-label={t("chat.thread.jumpBottomAria")}
          title={t("chat.thread.jumpBottomAria")}
          sx={{
            position: "absolute",
            right: 4,
            bottom: 8,
            zIndex: 2,
            border: `1px solid ${tk.border.strong}`,
            backgroundColor: tk.surface.panel,
            color: tk.text.secondary,
            "&:hover": { backgroundColor: tk.accent.softBg },
          }}
        >
          <KeyboardArrowDownRoundedIcon sx={{ fontSize: "1.15rem" }} />
        </IconButton>
      ) : null}

      <Box sx={{ height: "1px", flexShrink: 0, width: "100%" }} />
    </Box>
  );
}
