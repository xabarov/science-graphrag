import React from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import {
  BibliographyBlock,
  IdeaSuggestionsBlock,
  InventoryBlock,
  QuoteCandidatesBlock,
  RelationTraceBlock,
} from "../chat/ChatTypedBlocks.jsx";
import {
  AgentLiveStatus,
  AgentRunHeader,
  AgentSubagentRail,
  buildLiveStatusPresentation,
  deriveHeaderProgressHint,
  deriveRunState,
  humanizeUnknownCode,
  shouldShowSubagentRail,
  shouldSuppressPostRunStreamSummary,
} from "../../agent/index.js";
import MarkdownView from "../../markdown/MarkdownView.jsx";
import { AskSourceList } from "./AskSourceList.jsx";
import { mergeQuoteCandidatesIntoCitations } from "./citationHydration.js";
import { deriveAnswerClass } from "./askSourcePresentation.js";

/**
 * Detail-level matrix (product UX):
 * - simple: minimal chrome — no "Answer" section title, no post-run stream headline, no post-run specialist rail.
 * - detailed: full technical chrome — section title, post-run headline (when not suppressed), post-run rail when events exist.
 * Streaming keeps the specialist rail in both modes so users still see live routing during the turn.
 */

function formatAgentWarning(t, code) {
  const c = String(code || "").trim();
  if (!c) return "";
  const key = `chat.warnings.${c}`;
  const out = t(key);
  if (out && out !== key) return out;
  return humanizeUnknownCode(c) || c;
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   normalized: Record<string, unknown>,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   workspaceWorkId: string | null,
 *   workspaceId?: string,
 *   retrievalMode: string,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   streamEvents?: unknown[],
 *   isRunActive?: boolean,
 *   chatDetailLevel?: "simple" | "detailed",
 * }} props
 */
export function AskAnswerPanel({
  t,
  normalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  workspaceId = "",
  retrievalMode,
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  streamEvents = [],
  isRunActive = false,
  chatDetailLevel = "simple",
}) {
  void locked;
  void workId;
  void inWorkspace;
  void workspaceWorkId;
  void agentToolTrace;
  void retrievalJsonOpen;
  void onToggleRetrievalJson;

  const tk = useTheme().appTokens;
  if (!normalized) return null;

  const { runState } = deriveRunState({ normalized, isRunActive, streamEvents });
  const citations = mergeQuoteCandidatesIntoCitations(
    Array.isArray(normalized.citations) ? normalized.citations : [],
    Array.isArray(normalized.quote_candidates) ? normalized.quote_candidates : [],
    normalized.inventory && typeof normalized.inventory === "object" ? normalized.inventory : null,
  );
  const answerClass = deriveAnswerClass(normalized);
  /** Quote-style turns surface evidence in the answer + quote_candidates; structured citations are redundant. */
  const hideStructuredCitations = answerClass === "quote_extraction";
  const warningsList = Array.isArray(normalized.warnings) ? normalized.warnings : [];
  const hasWeakEvidence = warningsList.includes("weak_evidence");
  const answerText = String(normalized.answer || "").trim();
  const hasDegraded =
    (Array.isArray(normalized?.retrieval_trace?.degraded) && normalized.retrieval_trace.degraded.length > 0) ||
    (Array.isArray(normalized?.graph_context?.degraded) && normalized.graph_context.degraded.length > 0);

  const showSubagentRail = retrievalMode === "agent" && shouldShowSubagentRail(streamEvents);

  return (
    <Box>
      <AgentRunHeader
        t={t}
        runState={runState}
        progressHint={isRunActive ? "" : deriveHeaderProgressHint(t, streamEvents, isRunActive)}
      />

      {isRunActive && showSubagentRail ? (
        <AgentSubagentRail
          t={t}
          streamEvents={streamEvents}
          compact={chatDetailLevel === "simple"}
          chatDetailLevel={chatDetailLevel}
        />
      ) : null}

      {isRunActive ? (
        <AgentLiveStatus
          t={t}
          streamEvents={streamEvents}
          isActive
          embedded
          chatDetailLevel={chatDetailLevel}
        />
      ) : null}

      {warningsList.length > 0 ? (
        <Alert
          severity="warning"
          variant={hasWeakEvidence ? "outlined" : "standard"}
          sx={{
            mb: 1,
            fontSize: "0.75rem",
            ...(hasWeakEvidence
              ? {
                  backgroundColor: "rgba(251, 191, 36, 0.06)",
                  borderColor: "rgba(251, 191, 36, 0.42)",
                }
              : { backgroundColor: tk.surface.subtle }),
          }}
        >
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {warningsList.map((w) => (
              <Box component="li" key={String(w)} sx={{ mb: 0.25 }}>
                {formatAgentWarning(t, w)}
              </Box>
            ))}
          </Box>
        </Alert>
      ) : null}

      {hasDegraded ? (
        <Alert severity="info" sx={{ mb: 1, fontSize: "0.8125rem", backgroundColor: tk.surface.panelAlt }}>
          {t("askPanel.answer.degraded")}
        </Alert>
      ) : null}

      {!isRunActive ? (
        <>
          {chatDetailLevel === "detailed" ? (
            <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
              {t("chat.run.answerSectionTitle")}
            </Typography>
          ) : null}
          {answerText ? (
            <Box
              aria-live="polite"
              aria-atomic="true"
              sx={{
                mb: 1.25,
                "& .reader-markdown": {
                  fontSize: "0.8125rem",
                  lineHeight: 1.6,
                },
                "& .reader-markdown p:last-of-type": {
                  mb: 0,
                },
              }}
            >
              {/* Markdown links `[n](#ask-citation-n)` resolve to citation blocks (`id=ask-citation-n`) below. */}
              <MarkdownView markdown={answerText} data-testid="ask-answer-markdown" />
            </Box>
          ) : (
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap", mb: 1.25 }}>
              {t("workspace.upload.dash")}
            </Typography>
          )}
        </>
      ) : answerText ? (
        <>
          {chatDetailLevel === "detailed" ? (
            <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
              {t("chat.run.answerSectionTitle")}
            </Typography>
          ) : null}
          <Box
            sx={{
              mb: 1.25,
              "& .reader-markdown": {
                fontSize: "0.8125rem",
                lineHeight: 1.6,
              },
              "& .reader-markdown p:last-of-type": {
                mb: 0,
              },
            }}
          >
            {/* Markdown links `[n](#ask-citation-n)` resolve to citation blocks (`id=ask-citation-n`) below. */}
            <MarkdownView markdown={answerText} data-testid="ask-answer-markdown" />
          </Box>
        </>
      ) : null}

      {!isRunActive && chatDetailLevel === "detailed" && Array.isArray(streamEvents) && streamEvents.length > 0 ? (() => {
        if (shouldSuppressPostRunStreamSummary(streamEvents)) return null;
        const postRun = buildLiveStatusPresentation(t, streamEvents, false);
        if (!postRun.headline) return null;
        return (
          <Typography
            data-testid="post-run-stream-summary"
            sx={{ fontSize: "0.75rem", color: tk.text.muted, mb: 1, lineHeight: 1.45 }}
          >
            {postRun.headline}
          </Typography>
        );
      })() : null}

      {!isRunActive && showSubagentRail && chatDetailLevel === "detailed" ? (
        <AgentSubagentRail t={t} streamEvents={streamEvents} compact={false} chatDetailLevel={chatDetailLevel} />
      ) : null}

      {!isRunActive ? (
        <>
          <InventoryBlock
            t={t}
            inventory={normalized.inventory}
            chatDetailLevel={chatDetailLevel}
            citationCount={citations.length}
            hasWeakEvidence={hasWeakEvidence}
          />
          <QuoteCandidatesBlock
            key={chatDetailLevel}
            t={t}
            candidates={normalized.quote_candidates}
            chatDetailLevel={chatDetailLevel}
          />
          <BibliographyBlock t={t} bibliography={normalized.bibliography} chatDetailLevel={chatDetailLevel} />
          <RelationTraceBlock t={t} relationTrace={normalized.relation_trace} chatDetailLevel={chatDetailLevel} />
          <IdeaSuggestionsBlock t={t} suggestions={normalized.idea_suggestions} />
        </>
      ) : null}

      <AskSourceList
        t={t}
        citations={citations}
        answerClass={answerClass}
        workspaceId={workspaceId}
        isRunActive={isRunActive}
        hideStructuredCitations={hideStructuredCitations}
        chatDetailLevel={chatDetailLevel}
      />
    </Box>
  );
}
