import React from "react";
import { Link } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { GRAPH_PATH, READER_PATH } from "../../../routes/paths.js";
import { buildStandaloneEvidencePath, buildStandaloneTracePath } from "../traceability/traceabilityState.js";
import {
  BibliographyBlock,
  IdeaSuggestionsBlock,
  InventoryBlock,
  QuoteCandidatesBlock,
  RelationTraceBlock,
} from "./ChatTypedBlocks.jsx";
import {
  buildLiveStatusPresentation,
  deriveHeaderProgressHint,
  deriveRunState,
  shouldShowSubagentRail,
  shouldSuppressPostRunStreamSummary,
} from "../agent/agentRunViewModel.js";
import { humanizeUnknownCode } from "../agent/agentRunVocabulary.js";
import { AgentRunHeader } from "../agent/AgentRunHeader.jsx";
import { AgentLiveStatus } from "../agent/AgentLiveStatus.jsx";
import { AgentSubagentRail } from "../agent/AgentSubagentRail.jsx";
import MarkdownView from "../markdown/MarkdownView.jsx";
import { CitationBodyExpandable } from "./CitationBodyExpandable.jsx";
import { formatEvidenceSummaryForDisplay } from "./evidenceSummaryFormat.js";
import { extractTokenCountsFromRunMetadata } from "./runMetadataUsage.js";

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
  void agentToolTrace;
  void retrievalJsonOpen;
  void onToggleRetrievalJson;

  const tk = useTheme().appTokens;
  if (!normalized) return null;

  const { runState } = deriveRunState({ normalized, isRunActive, streamEvents });
  const citations = Array.isArray(normalized.citations) ? normalized.citations : [];
  const answerClass = normalized.answer_class != null ? String(normalized.answer_class).trim() : "";
  /** Quote-style turns surface evidence in the answer + quote_candidates; structured citations are redundant. */
  const hideStructuredCitations = answerClass === "quote_extraction";
  const warningsList = Array.isArray(normalized.warnings) ? normalized.warnings : [];
  const hasWeakEvidence = warningsList.includes("weak_evidence");
  const answerText = String(normalized.answer || "").trim();
  const hasDegraded =
    (Array.isArray(normalized?.retrieval_trace?.degraded) && normalized.retrieval_trace.degraded.length > 0) ||
    (Array.isArray(normalized?.graph_context?.degraded) && normalized.graph_context.degraded.length > 0);
  const wsForTrace = String(workspaceId || "").trim();
  const { totalTokens: headerTotalTokens } = extractTokenCountsFromRunMetadata(normalized.run_metadata);
  const evidenceSummaryDisplay = normalized.evidence_summary
    ? formatEvidenceSummaryForDisplay(t, normalized.evidence_summary)
    : "";

  const showSubagentRail = retrievalMode === "agent" && shouldShowSubagentRail(streamEvents);

  function citationTraceExtras(chunkFingerprint, sectionPath, citationIndex) {
    const base = { chunkFingerprint, section: sectionPath, citation: citationIndex };
    return wsForTrace ? { ...base, workspaceId: wsForTrace } : base;
  }

  return (
    <Box>
      <AgentRunHeader
        t={t}
        runState={runState}
        answerClass={normalized.answer_class}
        citationCount={citations.length}
        durationMs={normalized.duration_ms}
        totalTokens={headerTotalTokens}
        progressHint={isRunActive ? "" : deriveHeaderProgressHint(t, streamEvents, isRunActive)}
        defaultDetailsOpen={chatDetailLevel === "detailed"}
      />

      {isRunActive && showSubagentRail ? (
        <AgentSubagentRail
          t={t}
          streamEvents={streamEvents}
          compact={chatDetailLevel === "simple"}
        />
      ) : null}

      {isRunActive ? <AgentLiveStatus t={t} streamEvents={streamEvents} isActive embedded /> : null}

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

      {normalized.evidence_summary ? (
        <Box
          sx={{
            mb: 1.25,
            p: 1,
            borderRadius: "6px",
            border: `1px solid ${tk.border.default}`,
            backgroundColor: tk.surface.panelAlt,
          }}
        >
          <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: tk.text.muted, mb: 0.35 }}>
            {t("chat.typed.evidenceSummaryLabel")}
          </Typography>
          <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary, whiteSpace: "pre-wrap" }}>
            {evidenceSummaryDisplay}
          </Typography>
        </Box>
      ) : null}

      {!isRunActive ? (
        <>
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
            {t("chat.run.answerSectionTitle")}
          </Typography>
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
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
            {t("chat.run.answerSectionTitle")}
          </Typography>
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
            <MarkdownView markdown={answerText} data-testid="ask-answer-markdown" />
          </Box>
        </>
      ) : null}

      {!isRunActive && Array.isArray(streamEvents) && streamEvents.length > 0 ? (() => {
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

      {!isRunActive && showSubagentRail ? (
        <AgentSubagentRail
          t={t}
          streamEvents={streamEvents}
          compact={chatDetailLevel === "simple"}
        />
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

      {!hideStructuredCitations && (!isRunActive || citations.length > 0) ? (
        <>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5, color: tk.text.primary }}>
            {t("askPanel.citations.title")}
          </Typography>
          {citations.length === 0 ? (
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.secondary }}>{t("askPanel.citations.none")}</Typography>
          ) : (
            citations.map((c, i) => {
          const wid = c.work_id != null ? String(c.work_id) : "";
          const chunkFingerprint = c.chunk_fingerprint != null ? String(c.chunk_fingerprint) : "";
          const sectionPath = c.section_path != null ? String(c.section_path) : "";
          const citationIndex = String(i + 1);
          const sameAsWorkspace = inWorkspace && wid && wid === String(workspaceWorkId).trim();
          const rank =
            c.rank != null && String(c.rank).trim() !== ""
              ? String(c.rank)
              : c.citation_index != null && String(c.citation_index).trim() !== ""
                ? String(c.citation_index)
                : String(i + 1);
          const rawScore = c.score ?? c.relevance ?? c.retrieval_score ?? c.similarity;
          const numScore = rawScore != null && String(rawScore).trim() !== "" ? Number(rawScore) : NaN;
          const score = Number.isFinite(numScore) ? String(numScore) : t("workspace.upload.dash");
          return (
            <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: tk.text.secondary }}>
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>
                {t("askPanel.citation.line", { rank, score, work: wid || t("askPanel.citation.noWork") })}
              </Typography>
              {chatDetailLevel === "detailed" ? (
                <Typography
                  data-testid={`citation-chunk-fingerprint-${i}`}
                  sx={{ fontSize: "0.75rem", color: tk.text.muted, mt: 0.25 }}
                >
                  {t("askPanel.chunkLabel")} {String(c.chunk_fingerprint ?? t("workspace.upload.dash"))}
                </Typography>
              ) : null}
              {wid ? (
                <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {sameAsWorkspace ? (
                    <>
                      <Link
                        to={buildStandaloneTracePath(READER_PATH, wid, {
                          ...citationTraceExtras(chunkFingerprint, sectionPath, citationIndex),
                        })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openReader")}
                      </Link>
                      <Link
                        to={buildStandaloneEvidencePath(wid, citationTraceExtras(chunkFingerprint, sectionPath, citationIndex))}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openEvidence")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath(GRAPH_PATH, wid, {
                          ...citationTraceExtras(chunkFingerprint, sectionPath, citationIndex),
                        })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openGraph")}
                      </Link>
                    </>
                  ) : (
                    <>
                      <Link
                        to={buildStandaloneTracePath(READER_PATH, wid, {
                          ...citationTraceExtras(chunkFingerprint, sectionPath, citationIndex),
                        })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openInWorkspace")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath(READER_PATH, wid, citationTraceExtras(chunkFingerprint, sectionPath, citationIndex))}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneReader")}
                      </Link>
                      <Link
                        to={buildStandaloneEvidencePath(wid, citationTraceExtras(chunkFingerprint, sectionPath, citationIndex))}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneEvidence")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath(GRAPH_PATH, wid, citationTraceExtras(chunkFingerprint, sectionPath, citationIndex))}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneGraph")}
                      </Link>
                    </>
                  )}
                </Box>
              ) : null}
              <CitationBodyExpandable t={t} citation={c} />
            </Box>
          );
            })
          )}
        </>
      ) : null}
    </Box>
  );
}
