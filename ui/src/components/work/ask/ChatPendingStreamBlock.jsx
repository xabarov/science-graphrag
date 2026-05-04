import React from "react";
import Box from "@mui/material/Box";

import { AskAnswerPanel } from "./AskAnswerPanel.jsx";
import { AgentAssistantTurnShell } from "../agent/AgentAssistantTurnShell.jsx";
import { AgentRunHeader } from "../agent/AgentRunHeader.jsx";
import { AgentLiveStatus } from "../agent/AgentLiveStatus.jsx";
import ChatUserBubble from "./ChatUserBubble.jsx";

/**
 * Live pending user message + streaming or loading assistant region.
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
}) {
  return (
    <Box sx={{ mb: 2.25 }}>
      <ChatUserBubble text={pendingUserQuery} />
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
              />
            </AgentAssistantTurnShell>
          ) : isLoading ? (
            <AgentAssistantTurnShell dense sx={{ mt: 1 }}>
              <AgentRunHeader
                t={t}
                runState="running"
                answerClass={null}
                citationCount={0}
                durationMs={null}
                progressHint=""
                defaultDetailsOpen={chatDetailLevel === "detailed"}
              />
              <AgentLiveStatus t={t} streamEvents={streamEvents} isActive embedded />
            </AgentAssistantTurnShell>
          ) : null}
        </Box>
      </Box>
    </Box>
  );
}
