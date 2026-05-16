import React from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { AskAnswerPanel } from "../answer/AskAnswerPanel.jsx";
import {
  AgentAssistantTurnShell,
  AgentLiveStatus,
  AgentRunHeader,
} from "../../agent/index.js";
import ChatUserBubble from "./ChatUserBubble.jsx";
import { isPdfReadUserMessage } from "../../../../services/research/pdfReadUi.js";

/**
 * Live pending user message + streaming or loading assistant region.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   chatDetailLevel?: "simple" | "detailed",
 *   pendingUserQuery: string,
 *   liveNormalized: unknown | null,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   workspaceWorkId: string | null,
 *   workspaceId?: string,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   streamEvents: unknown[],
 *   isLoading: boolean,
 *   pdfReadingMode?: "off" | "ask" | "auto_safe_oa",
 *   onReadPdfSource?: (url: string) => void | Promise<void>,
 *   pdfReadState?: { isActive?: boolean, url?: string, error?: string, mode?: string, artifactId?: string } | null,
 * }} props
 */
export default function ChatPendingStreamBlock({
  t,
  chatDetailLevel = "simple",
  pendingUserQuery,
  liveNormalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  workspaceId,
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  streamEvents,
  isLoading,
  pdfReadingMode = "ask",
  onReadPdfSource = null,
  pdfReadState = null,
}) {
  const tk = useTheme().appTokens;
  const pendingBubbleText = isPdfReadUserMessage(pendingUserQuery)
    ? t("askPanel.pdfRead.userTurnLabel")
    : pendingUserQuery;
  const pdfProgressText =
    pdfReadState &&
    typeof pdfReadState === "object" &&
    pdfReadState.isActive &&
    String(pdfReadState.mode || "").trim() === "running"
      ? t("askPanel.pdfRead.progress", { url: String(pdfReadState.url || "") })
      : "";
  const pdfErrorText =
    pdfReadState &&
    typeof pdfReadState === "object" &&
    !pdfReadState.isActive &&
    String(pdfReadState.mode || "").trim() === "failed"
      ? String(pdfReadState.error || "").trim()
      : "";
  return (
    <Box sx={{ mb: 2.25 }}>
      <ChatUserBubble text={pendingBubbleText} />
      <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
        <Box sx={{ minWidth: 0, maxWidth: "min(880px, 100%)" }}>
          {liveNormalized ? (
            <AgentAssistantTurnShell dense sx={{ mt: 1 }}>
              <AskAnswerPanel
                t={t}
                normalized={liveNormalized}
                locked={locked}
                inWorkspace={inWorkspace}
                workId={workId}
                workspaceWorkId={workspaceWorkId}
                workspaceId={workspaceId}
                retrievalMode="agent"
                agentToolTrace={agentToolTrace}
                retrievalJsonOpen={retrievalJsonOpen}
                onToggleRetrievalJson={onToggleRetrievalJson}
                streamEvents={streamEvents}
                isRunActive={isLoading}
                chatDetailLevel={chatDetailLevel}
                pdfReadingMode={pdfReadingMode}
                onReadPdfSource={onReadPdfSource}
              />
              {pdfProgressText ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.72rem", color: tk.text.muted }}>
                  {pdfProgressText}
                </Typography>
              ) : null}
              {pdfErrorText ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.72rem", color: "rgba(239, 68, 68, 0.8)" }}>
                  {pdfErrorText}
                </Typography>
              ) : null}
            </AgentAssistantTurnShell>
          ) : isLoading ? (
            <AgentAssistantTurnShell dense sx={{ mt: 1 }}>
              <AgentRunHeader t={t} runState="running" progressHint="" />
              <AgentLiveStatus
                t={t}
                streamEvents={streamEvents}
                isActive
                embedded
                chatDetailLevel={chatDetailLevel}
              />
              {pdfProgressText ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.72rem", color: tk.text.muted }}>
                  {pdfProgressText}
                </Typography>
              ) : null}
              {pdfErrorText ? (
                <Typography sx={{ mt: 0.5, fontSize: "0.72rem", color: "rgba(239, 68, 68, 0.8)" }}>
                  {pdfErrorText}
                </Typography>
              ) : null}
            </AgentAssistantTurnShell>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
