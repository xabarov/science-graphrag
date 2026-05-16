import React, { useCallback, useMemo, useState } from "react";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import { useTheme } from "@mui/material/styles";

import { useFeedback } from "../../../feedback/index.js";
import ChatHistoryTurn from "./ChatHistoryTurn.jsx";
import ChatPendingStreamBlock from "./ChatPendingStreamBlock.jsx";
import ChatThreadMetadataDialog from "./ChatThreadMetadataDialog.jsx";
import AskUserQuestionForm from "../forms/AskUserQuestionForm.jsx";
import { ChatThreadEmptyState } from "./ChatThreadEmptyState.jsx";
import { extractTurnMetadata } from "./chatThreadMetrics.js";
import { useChatThreadScroll } from "./useChatThreadScroll.js";

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
 *   pdfReadingMode?: "off" | "ask" | "auto_safe_oa",
 *   onReadPdfSource?: (url: string) => void | Promise<void>,
 *   pdfReadState?: { isActive?: boolean, url?: string, error?: string, mode?: string, artifactId?: string } | null,
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
  pdfReadingMode = "ask",
  onReadPdfSource = null,
  pdfReadState = null,
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

  const { containerRef, stickToBottom, jumpToBottom } = useChatThreadScroll({
    chronologicalLength: chronological.length,
    pendingUserQuery,
    isLoading,
    liveNormalized,
    streamEvents,
    streamForThisChat,
    openStructuredQuestion,
  });

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
      {showEmptyState ? <ChatThreadEmptyState t={t} tk={tk} starterPromptKeys={starterPromptKeys} onStarterPrompt={onStarterPrompt} /> : null}

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
          pdfReadingMode={pdfReadingMode}
          onReadPdfSource={onReadPdfSource}
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
          pdfReadingMode={pdfReadingMode}
          onReadPdfSource={onReadPdfSource}
          pdfReadState={pdfReadState}
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
            jumpToBottom();
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
