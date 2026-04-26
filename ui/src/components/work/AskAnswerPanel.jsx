import React from "react";
import { Link } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { CursorSmallButton } from "../common/index.js";
import {
  buildAskAnswerRationale,
  formatRetrievalSummaryLines,
} from "../../services/researchApi.js";
import { buildStandaloneTracePath, buildWorkspaceTracePath } from "./traceabilityState.js";
import AgentToolTrace from "./AgentToolTrace.jsx";
import { BibliographyBlock, InventoryBlock, QuoteCandidatesBlock } from "./ChatTypedBlocks.jsx";

function FlagChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return <Box sx={{ mt: 1 }}><Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>{label}</Typography><Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>{items.map((d) => <Chip key={d} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />)}</Box></Box>;
}

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
  isStreaming = false,
}) {
  if (!normalized) return null;
  return (
    <Box sx={{ mt: 2, p: 2, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#1a1a1a" }}>
      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1 }}>{t("askPanel.answer.title")}</Typography>
      <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.72)", mb: 0.5 }}>{t("askPanel.answer.why")}</Typography>
      <Box component="ul" sx={{ m: 0, mb: 1.25, pl: 2.25, color: "rgba(255,255,255,0.62)", fontSize: "0.75rem", lineHeight: 1.5 }}>
        {buildAskAnswerRationale(normalized, { locked, inWorkspace, formWorkId: workId }).map((line, idx) => <Box component="li" key={idx} sx={{ mb: 0.35 }}>{line}</Box>)}
      </Box>
      {isStreaming ? <Box sx={{ mb: 1 }}>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.4)", fontSize: "0.7rem" }}>Agent thinking...</Typography>
        {streamEvents.filter((event) => event?.type === "tool_call").map((event, index) => <Box key={`${String(event?.step ?? index)}-${index}`} sx={{ display: "flex", alignItems: "center", gap: 0.5, py: 0.25, opacity: 0.7 }}>
          <Typography component="span" sx={{ fontSize: "0.7rem", fontFamily: "monospace", color: "rgba(129,140,248,0.9)" }}>{String(event?.tool || "tool")}</Typography>
          {event?.args_summary?.query ? <Typography component="span" sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)" }}>{`"${String(event.args_summary.query).slice(0, 40)}"`}</Typography> : null}
        </Box>)}
      </Box> : null}
      {Array.isArray(normalized.warnings) && normalized.warnings.length > 0 ? (
        <Alert severity="warning" sx={{ mb: 1, fontSize: "0.75rem", backgroundColor: "rgba(255,255,255,0.04)" }}>
          {normalized.warnings.map((w) => String(w)).join(" · ")}
        </Alert>
      ) : null}
      {normalized.answer_class ? (
        <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.35)", mb: 0.5 }}>{t("chat.typed.answerClass", { cls: String(normalized.answer_class) })}</Typography>
      ) : null}
      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.85)", whiteSpace: "pre-wrap" }}>{normalized.answer || t("workspace.upload.dash")}</Typography>
      <InventoryBlock t={t} inventory={normalized.inventory} />
      <QuoteCandidatesBlock t={t} candidates={normalized.quote_candidates} />
      <BibliographyBlock t={t} bibliography={normalized.bibliography} />
      {normalized.retrieval_trace.degraded.length > 0 || normalized.graph_context.degraded.length > 0 ? <Alert severity="info" sx={{ mt: 1.5, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.03)" }}>{t("askPanel.answer.degraded")}</Alert> : null}

      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.citations.title")}</Typography>
      {normalized.citations.length === 0 ? <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("askPanel.citations.none")}</Typography> : normalized.citations.map((c, i) => {
        const wid = c.work_id != null ? String(c.work_id) : "";
        const chunkFingerprint = c.chunk_fingerprint != null ? String(c.chunk_fingerprint) : "";
        const sectionPath = c.section_path != null ? String(c.section_path) : "";
        const citationIndex = String(i + 1);
        const sameAsWorkspace = inWorkspace && wid && wid === String(workspaceWorkId).trim();
        return <Box key={i} sx={{ mb: 1, fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}><Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)" }}>{t("askPanel.citation.line", { rank: String(c.rank), score: String(c.score), work: wid || t("askPanel.citation.noWork") })}</Typography><Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)", mt: 0.25 }}>{t("askPanel.chunkLabel")} {String(c.chunk_fingerprint ?? t("workspace.upload.dash"))}</Typography>{wid ? <Box sx={{ mt: 0.5, display: "flex", flexWrap: "wrap", gap: 1 }}>{sameAsWorkspace ? <><Link to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}>{t("askPanel.openReader")}</Link><Link to={buildWorkspaceTracePath(wid, "evidence", { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}>{t("askPanel.openEvidence")}</Link><Link to={buildWorkspaceTracePath(wid, "graph", { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}>{t("askPanel.openGraph")}</Link></> : <><Link to={buildWorkspaceTracePath(wid, "reader", { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.95)" }}>{t("askPanel.openInWorkspace")}</Link><Link to={buildStandaloneTracePath("/reader", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("askPanel.standaloneReader")}</Link><Link to={buildStandaloneTracePath("/evidence", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("askPanel.standaloneEvidence")}</Link><Link to={buildStandaloneTracePath("/graph", wid, { chunkFingerprint, section: sectionPath, citation: citationIndex })} style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.45)" }}>{t("askPanel.standaloneGraph")}</Link></>}</Box> : null}<Box component="span" sx={{ display: "block", color: "rgba(255,255,255,0.55)", mt: 0.25 }}>{String(c.excerpt ?? "").slice(0, 280)}{String(c.excerpt ?? "").length > 280 ? "…" : ""}</Box></Box>;
      })}

      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.graphContext.title")}</Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>{t("askPanel.graphContext.body", { semantic: String(normalized.graph_context.semantic_available), ctx: String(normalized.graph_context.context_work_id ?? "null"), err: normalized.graph_context.error ? ` error=${normalized.graph_context.error}` : "" })}</Typography>
      <FlagChips label={t("askPanel.flag.graphDegraded")} items={normalized.graph_context.degraded} />
      <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {normalized.graph_context.methods.map((m) => <Chip key={`m-${m}`} label={m} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />)}
        {normalized.graph_context.datasets.map((d) => <Chip key={`d-${d}`} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />)}
      </Box>

      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.retrieval.title")}</Typography>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.75 }}>{t("askPanel.retrieval.summary")}</Typography>
      {retrievalMode === "agent" ? <AgentToolTrace toolTrace={agentToolTrace} /> : null}
      <Box sx={{ mb: 1 }}>{formatRetrievalSummaryLines(normalized.retrieval_trace).map((line, idx) => <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>{line}</Typography>)}</Box>
      <CursorSmallButton type="button" onClick={onToggleRetrievalJson} sx={{ mb: 1 }}>{retrievalJsonOpen ? t("askPanel.toggleJson.hide") : t("askPanel.toggleJson.show")}</CursorSmallButton>
      <Collapse in={retrievalJsonOpen} timeout="auto" unmountOnExit>
        <Typography component="pre" sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)", whiteSpace: "pre-wrap", wordBreak: "break-word", m: 0, p: 1, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "rgba(0,0,0,0.25)" }}>
          {JSON.stringify({ qdrant_collection: normalized.retrieval_trace.qdrant_collection, top_k_requested: normalized.retrieval_trace.top_k_requested, citations_returned: normalized.retrieval_trace.citations_returned, hit_count: normalized.retrieval_trace.hit_count, retrieval_policy: normalized.retrieval_trace.retrieval_policy, filter_work_id: normalized.retrieval_trace.filter_work_id, resolved_work_id: normalized.retrieval_trace.resolved_work_id, embedding: normalized.retrieval_trace.embedding, degraded: normalized.retrieval_trace.degraded }, null, 2)}
        </Typography>
      </Collapse>
    </Box>
  );
}
