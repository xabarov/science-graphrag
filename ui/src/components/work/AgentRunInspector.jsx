import React, { useState } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { CursorSmallButton } from "../common/index.js";
import { buildAskAnswerRationale, formatRetrievalSummaryLines } from "../../services/researchApi.js";
import AgentToolTrace from "./AgentToolTrace.jsx";
import { AgentStreamEventLines } from "./agentStreamEventLines.jsx";
import { shouldOfferRunInspector } from "./agentRunViewModel.js";

function FlagChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return (
    <Box sx={{ mt: 1 }}>
      <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>{label}</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {items.map((d) => (
          <Chip key={d} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
        ))}
      </Box>
    </Box>
  );
}

/**
 * Collapsed diagnostics: stream, rationale, tool trace, graph/retrieval detail.
 *
 * @param {{
 *   t: (key: string, vars?: Record<string, string>) => string,
 *   normalized: Record<string, unknown>,
 *   locked: boolean,
 *   inWorkspace: boolean,
 *   workId: string,
 *   retrievalMode: string,
 *   agentToolTrace: unknown[],
 *   streamEvents: unknown[],
 *   retrievalJsonOpen: boolean,
 *   onToggleRetrievalJson: () => void,
 *   defaultOpen?: boolean,
 * }} props
 */
export function AgentRunInspector({
  t,
  normalized,
  locked,
  inWorkspace,
  workId,
  retrievalMode,
  agentToolTrace,
  streamEvents = [],
  retrievalJsonOpen,
  onToggleRetrievalJson,
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(Boolean(defaultOpen));

  const offer = shouldOfferRunInspector({
    normalized,
    streamEvents,
    agentToolTrace,
    retrievalMode,
  });

  if (!offer) return null;

  const rationale = buildAskAnswerRationale(normalized, { locked, inWorkspace, formWorkId: workId });
  const rt = normalized.retrieval_trace && typeof normalized.retrieval_trace === "object" ? normalized.retrieval_trace : {};
  const phoenixUiBase =
    typeof import.meta.env?.VITE_PHOENIX_UI_BASE_URL === "string"
      ? import.meta.env.VITE_PHOENIX_UI_BASE_URL.trim()
      : "";
  const phoenixProjectId =
    typeof import.meta.env?.VITE_PHOENIX_PROJECT_ID === "string" &&
    import.meta.env.VITE_PHOENIX_PROJECT_ID.trim()
      ? import.meta.env.VITE_PHOENIX_PROJECT_ID.trim()
      : "science-graphrag";
  const phoenixTraceId =
    normalized.phoenix_trace_id != null && String(normalized.phoenix_trace_id).trim()
      ? String(normalized.phoenix_trace_id).trim()
      : "";
  const phoenixTraceUrl =
    phoenixUiBase && phoenixTraceId
      ? `${phoenixUiBase.replace(/\/$/, "")}/projects/${encodeURIComponent(
          phoenixProjectId,
        )}/traces/${encodeURIComponent(phoenixTraceId)}`
      : "";

  return (
    <Box sx={{ mt: 1.5, pt: 1, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
      <CursorSmallButton
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="agent-run-inspector-panel"
        aria-label={open ? t("chat.run.inspectToggleHideAria") : t("chat.run.inspectToggleShowAria")}
        id="agent-run-inspector-toggle"
        sx={{ mb: open ? 1 : 0 }}
      >
        {open ? t("chat.run.inspectToggleHide") : t("chat.run.inspectToggleShow")}
      </CursorSmallButton>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <Box id="agent-run-inspector-panel" role="region" aria-label={t("chat.run.inspectTitle")}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.75 }}>
            {t("chat.run.inspectTitle")}
          </Typography>

          <Typography sx={{ fontWeight: 600, fontSize: "0.72rem", color: "rgba(255,255,255,0.42)", mb: 0.35 }}>
            {t("chat.run.rationaleTitle")}
          </Typography>
          <Box component="ul" sx={{ m: 0, mb: 1.25, pl: 2, color: "rgba(255,255,255,0.55)", fontSize: "0.72rem", lineHeight: 1.45 }}>
            {rationale.map((line, idx) => (
              <Box component="li" key={idx} sx={{ mb: 0.35 }}>
                {line}
              </Box>
            ))}
          </Box>

          <AgentStreamEventLines t={t} events={streamEvents} />

          {retrievalMode === "agent" ? <AgentToolTrace toolTrace={agentToolTrace} /> : null}

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 1.5, mb: 0.5 }}>{t("askPanel.graphContext.title")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
            {t("askPanel.graphContext.body", {
              semantic: String(normalized.graph_context?.semantic_available ?? false),
              ctx: String(normalized.graph_context?.context_work_id ?? "null"),
              err: normalized.graph_context?.error ? ` error=${normalized.graph_context.error}` : "",
            })}
          </Typography>
          <FlagChips label={t("askPanel.flag.graphDegraded")} items={Array.isArray(normalized.graph_context?.degraded) ? normalized.graph_context.degraded : []} />
          <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
            {(Array.isArray(normalized.graph_context?.methods) ? normalized.graph_context.methods : []).map((m) => (
              <Chip key={`m-${m}`} label={m} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
            {(Array.isArray(normalized.graph_context?.datasets) ? normalized.graph_context.datasets : []).map((d) => (
              <Chip key={`d-${d}`} label={d} size="small" sx={{ height: 22, fontSize: "0.75rem" }} />
            ))}
          </Box>

          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.5 }}>{t("askPanel.retrieval.title")}</Typography>
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", mb: 0.75 }}>{t("askPanel.retrieval.summary")}</Typography>
          <Box sx={{ mb: 1 }}>
            {formatRetrievalSummaryLines(rt).map((line, idx) => (
              <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.45 }}>
                {line}
              </Typography>
            ))}
          </Box>
          <CursorSmallButton type="button" onClick={onToggleRetrievalJson} sx={{ mb: 1 }}>
            {retrievalJsonOpen ? t("askPanel.toggleJson.hide") : t("askPanel.toggleJson.show")}
          </CursorSmallButton>
          <Collapse in={retrievalJsonOpen} timeout="auto" unmountOnExit>
            <Typography
              component="pre"
              sx={{
                fontSize: "0.7rem",
                color: "rgba(255,255,255,0.5)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                m: 0,
                p: 1,
                borderRadius: "6px",
                border: "1px solid rgba(255,255,255,0.08)",
                backgroundColor: "rgba(0,0,0,0.25)",
              }}
            >
              {JSON.stringify(
                {
                  qdrant_collection: rt.qdrant_collection,
                  top_k_requested: rt.top_k_requested,
                  citations_returned: rt.citations_returned,
                  hit_count: rt.hit_count,
                  retrieval_policy: rt.retrieval_policy,
                  filter_work_id: rt.filter_work_id,
                  resolved_work_id: rt.resolved_work_id,
                  embedding: rt.embedding,
                  degraded: rt.degraded,
                },
                null,
                2,
              )}
            </Typography>
          </Collapse>

          {phoenixTraceUrl ? (
            <Typography
              component="a"
              href={phoenixTraceUrl}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={t("chat.run.openPhoenixAria")}
              sx={{
                display: "inline-block",
                fontSize: "0.72rem",
                color: "rgba(129, 140, 248, 0.95)",
                mt: 1,
                textDecoration: "none",
                borderBottom: "1px solid rgba(99, 102, 241, 0.35)",
                "&:hover": { borderBottomColor: "rgba(129, 140, 248, 0.7)" },
              }}
            >
              {t("chat.run.openPhoenix")}
            </Typography>
          ) : phoenixTraceId ? (
            <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)", mt: 1, fontFamily: "monospace" }}>
              {t("chat.run.phoenixTraceHint", { id: phoenixTraceId.slice(0, 24) })}
            </Typography>
          ) : null}
        </Box>
      </Collapse>
    </Box>
  );
}
