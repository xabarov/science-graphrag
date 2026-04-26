import React from "react";
import { Link } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { buildStandaloneTracePath, buildWorkspaceTracePath } from "./traceabilityState.js";
import {
  BibliographyBlock,
  IdeaSuggestionsBlock,
  InventoryBlock,
  QuoteCandidatesBlock,
  RelationTraceBlock,
} from "./ChatTypedBlocks.jsx";
import { deriveRunState } from "./agentRunViewModel.js";
import { AgentRunHeader } from "./AgentRunHeader.jsx";
import { AgentLiveStatus } from "./AgentLiveStatus.jsx";
import { AgentRunInspector } from "./AgentRunInspector.jsx";
import { AgentSubagentRail } from "./AgentSubagentRail.jsx";

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
  if (!normalized) return null;

  const { runState } = deriveRunState({ normalized, isRunActive, streamEvents });
  const citations = Array.isArray(normalized.citations) ? normalized.citations : [];
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

      {retrievalMode === "agent" && Array.isArray(streamEvents) && streamEvents.length > 0 ? (
        <AgentSubagentRail t={t} streamEvents={streamEvents} />
      ) : null}

      {isRunActive ? <AgentLiveStatus t={t} streamEvents={streamEvents} isActive /> : null}

      {Array.isArray(normalized.warnings) && normalized.warnings.length > 0 ? (
        <Alert severity="warning" sx={{ mb: 1, fontSize: "0.75rem", backgroundColor: "rgba(255,255,255,0.04)" }}>
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
        <Alert severity="info" sx={{ mb: 1, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.03)" }}>
          {t("askPanel.answer.degraded")}
        </Alert>
      ) : null}

      {normalized.evidence_summary ? (
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 1, whiteSpace: "pre-wrap" }}>
          {t("chat.typed.evidenceSummaryLabel")}: {String(normalized.evidence_summary)}
        </Typography>
      ) : null}

      <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mb: 0.5 }}>
        {t("chat.run.answerSectionTitle")}
      </Typography>
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", whiteSpace: "pre-wrap", mb: 1.25 }}>
        {normalized.answer || t("workspace.upload.dash")}
      </Typography>

      <InventoryBlock t={t} inventory={normalized.inventory} />
      <QuoteCandidatesBlock t={t} candidates={normalized.quote_candidates} />
      <BibliographyBlock t={t} bibliography={normalized.bibliography} />
      <RelationTraceBlock t={t} relationTrace={normalized.relation_trace} />
      <IdeaSuggestionsBlock t={t} suggestions={normalized.idea_suggestions} />

      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.citations.title")}</Typography>
      {citations.length === 0 ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.citations.none")}</Typography>
      ) : (
        citations.map((c, i) => {
          const wid = c.work_id != null ? String(c.work_id) : "";
          const chunkFingerprint = c.chunk_fingerprint != null ? String(c.chunk_fingerprint) : "";
          const sectionPath = c.section_path != null ? String(c.section_path) : "";
          const citationIndex = String(i + 1);
          const sameAsWorkspace = inWorkspace && wid && wid === String(workspaceWorkId).trim();
          return (
            <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>
                {t("askPanel.citation.line", { rank: String(c.rank), score: String(c.score), work: wid || t("askPanel.citation.noWork") })}
              </Typography>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>
                {t("askPanel.chunkLabel")} {String(c.chunk_fingerprint ?? t("workspace.upload.dash"))}
              </Typography>
              {wid ? (
                <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {sameAsWorkspace ? (
                    <>
                      <Link
                        to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                      >
                        {t("askPanel.openReader")}
                      </Link>
                      <Link
                        to={buildWorkspaceTracePath(wid, "evidence", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                      >
                        {t("askPanel.openEvidence")}
                      </Link>
                      <Link
                        to={buildWorkspaceTracePath(wid, "graph", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                      >
                        {t("askPanel.openGraph")}
                      </Link>
                    </>
                  ) : (
                    <>
                      <Link
                        to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}
                      >
                        {t("askPanel.openInWorkspace")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/reader", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                      >
                        {t("askPanel.standaloneReader")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/evidence", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                      >
                        {t("askPanel.standaloneEvidence")}
                      </Link>
                      <Link
                        to={buildStandaloneTracePath("/graph", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })}
                        style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}
                      >
                        {t("askPanel.standaloneGraph")}
                      </Link>
                    </>
                  )}
                </Box>
              ) : null}
              <Box component="span" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mt: 0.25 }}>
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
