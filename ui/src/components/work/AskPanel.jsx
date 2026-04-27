import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorButton, CursorDangerButton } from "../common/index.js";
import { FeedbackShell, useFeedback } from "../feedback/index.js";
import { ChatComposer } from "./ChatComposer.jsx";
import { ChatMessageThread } from "./ChatMessageThread.jsx";
import { ChatSessionSidebar } from "./ChatSessionSidebar.jsx";
import { AskPanelChrome } from "./AskPanelChrome.jsx";
import { useAskPanelOrchestration } from "./useAskPanelOrchestration.js";

/** Ask / chat workspace — composition shell; logic in `useAskPanelOrchestration`. */
export default function AskPanel({
  scopedWorkId = null,
  initialWorkId = "",
  showPageChrome = true,
  workspaceWorkId = null,
  workspaceId = "",
  urlSessionId = "",
  onUrlSessionIdChange,
  fillAvailableHeight = false,
}) {
  const { confirm } = useFeedback();
  const o = useAskPanelOrchestration({
    scopedWorkId,
    initialWorkId,
    workspaceWorkId,
    workspaceId,
    urlSessionId,
    onUrlSessionIdChange,
  });

  const handleDeleteSessionRequest = async (session) => {
    const n = Array.isArray(session?.entries) ? session.entries.length : 0;
    if (n > 0) {
      const ok = await confirm({
        title: o.t("chat.sidebar.deleteDialogTitle"),
        body: o.t("chat.sidebar.deleteConfirm"),
        variant: "danger",
        confirmLabel: o.t("chat.sidebar.deleteConfirmButton"),
        cancelLabel: o.t("chat.clear.cancel"),
      });
      if (!ok) return;
    }
    void o.onDeleteSession(session.id);
  };

  return (
    <Box
      sx={{
        width: "100%",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        ...(fillAvailableHeight
          ? { flex: 1, minHeight: 0, height: "100%" }
          : {
              minHeight: { xs: "min(100dvh - 140px, 720px)", md: "min(calc(100dvh - 160px), 900px)" },
              maxHeight: { md: "calc(100dvh - 160px)" },
            }),
      }}
    >
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: { xs: "column", md: "row" },
          gap: { xs: 1.5, md: 2 },
          alignItems: "stretch",
        }}
      >
        <ChatSessionSidebar
          t={o.t}
          sessionList={o.sessionList}
          activeSessionId={o.activeSessionId}
          onActiveSessionChange={o.onActiveSessionChange}
          onNewSession={o.onNewSession}
          onDeleteSessionRequest={handleDeleteSessionRequest}
          sx={{ flex: { xs: "0 0 auto", md: "0 0 auto" }, maxHeight: { xs: "min(40vh, 320px)", md: "none" } }}
        />
        <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: "flex", flexDirection: "column", gap: 0.5 }}>
          <AskPanelChrome
            showPageChrome={showPageChrome}
            t={o.t}
            scopeEyebrow={o.scopeEyebrow}
            error={o.error}
            onClearChatClick={showPageChrome ? undefined : o.openClearChatDialog}
            clearChatDisabled={o.isLoading}
          />
          <ChatMessageThread
            t={o.t}
            scopeKey={o.scopeKey}
            activeSessionId={o.activeSessionId}
            streamingTarget={o.streamingTarget}
            history={o.history}
            pendingUserQuery={o.pendingUserQuery}
            isLoading={o.isLoading}
            streamEvents={o.streamEvents}
            liveNormalized={o.normalized}
            locked={o.locked}
            inWorkspace={o.inWorkspace}
            workId={o.workId}
            workspaceWorkId={workspaceWorkId}
            agentToolTrace={o.agentToolTrace}
            retrievalJsonOpen={o.retrievalJsonOpen}
            onToggleRetrievalJson={() => o.setRetrievalJsonOpen((v) => !v)}
            starterPromptKeys={o.starterPromptKeys}
            onStarterPrompt={o.setQuery}
            onCopyUserText={o.onCopyUserText}
            onRestartFromTurn={o.onRestartFromTurn}
            onCopyAssistantEntry={o.onCopyAssistantEntry}
            restartDisabled={o.isLoading}
          />
          <ChatComposer
            t={o.t}
            query={o.query}
            onQueryChange={o.setQuery}
            loading={o.isLoading}
            onSubmit={o.onSubmit}
            inWorkspace={o.inWorkspace}
            standaloneChatPath={o.standaloneChatPath}
            locked={o.locked}
            scopedWorkId={scopedWorkId}
            workspaceId={workspaceId}
            workId={o.workId}
            onWorkIdChange={o.handleWorkIdChange}
            onArticlePicked={o.onArticlePicked}
            onWorkSearch={o.searchWorks}
            resolvedWork={o.workDetailsForChip}
            corpusWorkspaceOnly={o.corpusWorkspaceOnly}
            standaloneMode={o.standaloneMode}
            answerClassHint={o.answerClassHint}
            onAnswerClassHintChange={o.setAnswerClassHint}
            streamingHint={o.streamingHint}
          />
        </Box>
      </Box>

      <FeedbackShell
        open={o.clearChatDialogOpen}
        onClose={() => o.setClearChatDialogOpen(false)}
        title={o.t("chat.clear.dialogTitle")}
        titleId="chat-clear-dialog-title"
        aria-describedby="chat-clear-dialog-desc"
        actions={
          <>
            <CursorButton type="button" size="small" onClick={() => o.setClearChatDialogOpen(false)} sx={{ color: "rgba(255,255,255,0.7)" }}>
              {o.t("chat.clear.cancel")}
            </CursorButton>
            <CursorDangerButton type="button" size="small" disabled={o.isLoading} onClick={() => void o.onClearChat()}>
              {o.t("chat.clear.confirm")}
            </CursorDangerButton>
          </>
        }
      >
        <Typography id="chat-clear-dialog-desc" component="span" sx={{ display: "block" }}>
          {o.t("chat.clear.dialogBody")}
        </Typography>
      </FeedbackShell>
    </Box>
  );
}
