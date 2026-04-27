import React from "react";
import { Link } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { buildStandaloneTracePath, buildWorkspaceTracePath } from "./traceabilityState.js";
import {
  BibliographyBlock,
  IdeaSuggestionsBlock,
  InventoryBlock,
  QuoteCandidatesBlock,
  RelationTraceBlock,
} from "./ChatTypedBlocks.jsx";
import { deriveRunState, shouldShowSubagentRail } from "./agentRunViewModel.js";
import { AgentRunHeader } from "./AgentRunHeader.jsx";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";
import { AgentRunInspector } from "./AgentRunInspector.jsx";
import { AgentSubagentRail } from "./AgentSubagentRail.jsx";
import MarkdownView from "./MarkdownView.jsx";

function formatAgentWarning(t, code) {
  const c = String(code || "").trim();
  if (!c) return "";
  const key = `chat.warnings.${c}`;
  const out = t(key);
  return out === key ? c : out;
}

/**
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   normalized: Record<string, unknown>,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   workspaceWorkId: string | null,
 *   retrievalMode: string,
 *   agentToolTrace: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   streamEvents?: unknown[],
 *   isRunActive?: boolean,
 * }} props
 */
export function AskAnswerPanel({
  t,
  normalized,
  locked,
  inWorkspace,
  workId,
  workspaceWorkId,
  retrievalMode,
  agentToolTrace,
  retrievalJsonOpen,
  onToggleRetrievalJson,
  streamEvents = [],
  isRunActive = false,
}) {
  const tk = useTheme().appTokens;
  if (!normalized) return null;

  const { runState } = deriveRunState({ normalized, isRunActive, streamEvents });
  const citations = Array.isArray(normalized.citations) ? normalized.citations : [];
  const answerText = String(normalized.answer || "").trim();
  const hasDegraded =
    (Array.isArray(normalized?.retrieval_trace?.degraded) && normalized.retrieval_trace.degraded.length > 0) ||
    (Array.isArray(normalized?.graph_context?.degraded) && normalized.graph_context.degraded.length > 0);

  return (
    <Box>
      <AgentRunHeader
        t={t}
        runState={runState}
        answerClass={normalized.answer_class}
        citationCount={citations.length}
        durationMs={normalized.duration_ms}
        streamEventCount={Array.isArray(streamEvents) ? streamEvents.length : 0}
      />

      {retrievalMode === "agent" && shouldShowSubagentRail(streamEvents) ? (
        <AgentSubagentRail t={t} streamEvents={streamEvents} />
      ) : null}

      {isRunActive ? <AgentLiveStatus t={t} streamEvents={streamEvents} isActive /> : null}

      {Array.isArray(normalized.warnings) && normalized.warnings.length > 0 ? (
        <Alert severity="warning" sx={{ mb: 1, fontSize: "0.75rem", backgroundColor: tk.surface.subtle }}>
          <Box component="ul" sx={{ m: 0, pl: 2 }}>
            {normalized.warnings.map((w) => (
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
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 1, whiteSpace: "pre-wrap" }}>
          {t("chat.typed.evidenceSummaryLabel")}: {String(normalized.evidence_summary)}
        </Typography>
      ) : null}

      {!isRunActive && normalized.session_summary_excerpt ? (
        <Box
          sx={{
            mb: 1.25,
            p: 1,
            borderRadius: "6px",
            border: `1px solid ${tk.border.default}`,
            backgroundColor: tk.surface.panelAlt,
          }}
        >
          <Typography sx={{ fontSize: "0.7rem", fontWeight: 600, color: tk.text.muted, mb: 0.5 }}>
            {t("chat.sessionMemory.title")}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, whiteSpace: "pre-wrap" }}>
            {String(normalized.session_summary_excerpt)}
          </Typography>
          {normalized.run_metadata?.compaction?.kinds?.length ? (
            <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint, mt: 0.75 }}>
              {t("chat.sessionMemory.compactionKinds")}: {normalized.run_metadata.compaction.kinds.join(", ")}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: tk.text.muted, mb: 0.5 }}>
        {t("chat.run.answerSectionTitle")}
      </Typography>
      {answerText ? (
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
      ) : (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, whiteSpace: "pre-wrap", mb: 1.25 }}>
          {t("workspace.upload.dash")}
        </Typography>
      )}

      <InventoryBlock t={t} inventory={normalized.inventory} />
      <QuoteCandidatesBlock t={t} candidates={normalized.quote_candidates} />
      <BibliographyBlock t={t} bibliography={normalized.bibliography} />
      <RelationTraceBlock t={t} relationTrace={normalized.relation_trace} />
      <IdeaSuggestionsBlock t={t} suggestions={normalized.idea_suggestions} />

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
          return (
            <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: tk.text.secondary }}>
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary }}>
                {t("askPanel.citation.line", { rank: String(c.rank), score: String(c.score), work: wid || t("askPanel.citation.noWork") })}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mt: 0.25 }}>
                {t("askPanel.chunkLabel")} {String(c.chunk_fingerprint ?? t("workspace.upload.dash"))}
              </Typography>
              {wid ? (
                <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {sameAsWorkspace ? (
                    <>
                      <Link
                        to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openReader")}
                      </Link>
                      <Link
                        to={buildWorkspaceTracePath(wid, "evidence", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openEvidence")}
                      </Link>
                      <Link
                        to={buildWorkspaceTracePath(wid, "graph", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openGraph")}
                      </Link>
                    </>
                  ) : (
                    <>
                      <Link
                        to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.accent }}
                      >
                        {t("askPanel.openInWorkspace")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/reader", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneReader")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/evidence", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneEvidence")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/graph", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: tk.text.muted }}
                      >
                        {t("askPanel.standaloneGraph")}
                      </Link>
                    </>
                  )}
                </Box>
              ) : null}
              <Box component="span" sx={{ display: "block", color: tk.text.secondary, mt: 0.25 }}>
                {String(c.excerpt ?? "").slice(0, 280)}
                {String(c.excerpt ?? "").length > 280 ? "…" : ""}
              </Box>
            </Box>
          );
        })
      )}

      <AgentRunInspector
        t={t}
        normalized={normalized}
        locked={locked}
        inWorkspace={inWorkspace}
        workId={workId}
        retrievalMode={retrievalMode}
        agentToolTrace={agentToolTrace}
        streamEvents={streamEvents}
        retrievalJsonOpen={retrievalJsonOpen}
        onToggleRetrievalJson={onToggleRetrievalJson}
      />
    </Box>
  );
}
