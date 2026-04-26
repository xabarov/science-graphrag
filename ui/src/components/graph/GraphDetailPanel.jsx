import React, { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { useI18n } from "../../i18n/I18nContext.jsx";
import { CursorSmallButton } from "../common/index.js";
import {
  localizeAggregatorSubtitle,
  localizeAggregatorTitle,
  localizeDirectionHintTooltip,
  localizeEdgeType,
  localizeNodeKind,
  localizeWorkPropertyKey,
} from "./graphLocalize.js";

/**
 * @param {unknown} v
 */
function formatPropertyValue(v) {
  if (v == null) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

/**
 * @param {string} hint
 * @param {(k: string) => string} t
 */
function localizeDirectionHint(hint, t) {
  const h = String(hint || "").trim().toLowerCase();
  if (!h) return "";
  const key = `graph.detailPanel.direction.${h}`;
  const out = t(key);
  return out !== key ? out : hint;
}

/**
 * @param {{
 *   selectedNode: { id: string, label: string, type: string, displayLabel?: string, subtitle?: string, nodeKind?: string, properties?: Record<string, unknown>, raw: object } | null,
 *   selectedEdge: { id: string, source: string, target: string, type: string, displayType?: string, sourceLabel?: string, targetLabel?: string, summary?: string, raw: object } | null,
 *   relatedEdges: Array<object>,
 *   relatedEdgeRows?: Array<{ edge: object, otherId: string, otherLabel: string, readableLine: string, directionHint: string }>,
 *   selectedEdgeReadable?: string,
 *   graphMeta?: Record<string, unknown>,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 *   onExpandWorkspaceNeighbors?: () => void | Promise<void>,
 *   onAggregatorExpand?: (node: object, expandEndpoint: string) => void | Promise<void>,
 *   expandWorkspaceNeighborsBusy?: boolean,
 *   mode?: "embedded" | "standalone",
 * }} props
 */
export default function GraphDetailPanel({
  selectedNode,
  selectedEdge,
  relatedEdges = [],
  relatedEdgeRows = [],
  selectedEdgeReadable = "",
  graphMeta = {},
  onSelectNode,
  onSelectEdge,
  onExpandWorkspaceNeighbors,
  onAggregatorExpand,
  expandWorkspaceNeighborsBusy = false,
  mode = "embedded",
}) {
  const { t } = useI18n();
  const compact = mode === "embedded" || mode === "standalone";
  const [rawOpen, setRawOpen] = useState(false);
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  const truncated = Boolean(graphMeta?.is_truncated);
  const neighborLimit = graphMeta?.neighbor_limit_applied;
  const neighborCount = graphMeta?.neighbor_match_count;
  const truncatedLimitClause =
    neighborLimit != null ? t("graph.detailPanel.truncatedLimitClause", { neighborLimit: String(neighborLimit) }) : "";

  return (
    <Box
      component="aside"
      role="region"
      aria-label={t("graph.detailPanel.title")}
      sx={{
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        backgroundColor: "#1a1a1a",
        p: compact ? 1.5 : 2,
        flex: 1,
        minHeight: mode === "standalone" ? 0 : compact ? 280 : 360,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Typography component="h2" sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1, flexShrink: 0 }}>
        {t("graph.detailPanel.title")}
      </Typography>

      {truncated ? (
        <Box
          sx={{
            mb: 1,
            p: 1,
            borderRadius: "6px",
            border: "1px solid rgba(99,102,241,0.25)",
            backgroundColor: "rgba(99,102,241,0.08)",
            flexShrink: 0,
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.78)", lineHeight: 1.45 }}>
            {t("graph.detailPanel.truncatedLine", {
              neighborCount: neighborCount != null ? String(neighborCount) : "?",
              limitClause: truncatedLimitClause,
            })}
          </Typography>
        </Box>
      ) : null}

      {!selectedNode && !selectedEdge ? (
        <Typography
          sx={{
            fontSize: mode === "standalone" ? "0.75rem" : "0.8125rem",
            color: "rgba(255,255,255,0.45)",
            lineHeight: 1.4,
          }}
        >
          {mode === "standalone" ? t("graph.detailPanel.emptyStandalone") : t("graph.detailPanel.emptyEmbedded")}
        </Typography>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.25 }}>
        {selectedEdge ? (
          <>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>{t("graph.detailPanel.relationship")}</Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", lineHeight: 1.45, mb: 1 }}>
              {selectedEdgeReadable ||
                `${selectedEdge.sourceLabel || selectedEdge.source} —[${localizeEdgeType(selectedEdge, t)}]→ ${selectedEdge.targetLabel || selectedEdge.target}`}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.9)", mb: 0.5 }}>
              {localizeEdgeType(selectedEdge, t)}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1 }}>
              <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.source)}>
                {t("graph.detailPanel.openSource")}
              </CursorSmallButton>
              <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.target)}>
                {t("graph.detailPanel.openTarget")}
              </CursorSmallButton>
            </Box>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.38)", fontFamily: "monospace", wordBreak: "break-all" }}>
              id: {selectedEdge.id}
            </Typography>
          </>
        ) : null}

        {selectedNode ? (
          <>
            {String(selectedNode.nodeKind) === "Aggregator" ? (
              <Box sx={{ mb: 1.5 }}>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.92)" }}>{t("graph.aggregator.badge")}</Typography>
                <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", mt: 0.25 }}>
                  {localizeAggregatorTitle(selectedNode, t)}
                </Typography>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mt: 0.35 }}>
                  {localizeAggregatorSubtitle(t)}
                </Typography>
                {Array.isArray(selectedNode.raw?.aggregation_hints?.preview_labels) &&
                selectedNode.raw.aggregation_hints.preview_labels.length > 0 ? (
                  <List dense sx={{ py: 0.5 }}>
                    {selectedNode.raw.aggregation_hints.preview_labels.map((label) => (
                      <ListItem key={String(label)} sx={{ px: 0 }}>
                        <ListItemText primary={String(label)} />
                      </ListItem>
                    ))}
                  </List>
                ) : null}
                <CursorSmallButton
                  type="button"
                  disabled={expandWorkspaceNeighborsBusy}
                  onClick={() =>
                    onAggregatorExpand?.(selectedNode, String(selectedNode.raw?.aggregation_hints?.expand_endpoint || ""))
                  }
                >
                  {expandWorkspaceNeighborsBusy
                    ? t("graph.aggregator.loading")
                    : t("graph.aggregator.expandAll", {
                        count: String(selectedNode.raw?.aggregation_hints?.count || 0),
                      })}
                </CursorSmallButton>
              </Box>
            ) : null}
            {String(selectedNode.nodeKind) !== "Aggregator" ? (
              <>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.92)" }}>
                  {localizeNodeKind(selectedNode, t)}
                </Typography>
                <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", mt: 0.25, lineHeight: 1.35 }}>
                  {selectedNode.displayLabel || selectedNode.label}
                </Typography>
                {selectedNode.subtitle ? (
                  <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mt: 0.35 }}>{selectedNode.subtitle}</Typography>
                ) : null}
              </>
            ) : null}

            {String(selectedNode.type) === "Work" &&
            (selectedNode.workspaceMembership ||
              selectedNode.internalCiteCount != null ||
              selectedNode.externalCiteCount != null) ? (
              <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
                {selectedNode.workspaceMembership ? (
                  <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.5)", fontFamily: "monospace" }}>
                    {String(selectedNode.workspaceMembership)}
                  </Typography>
                ) : null}
                {selectedNode.internalCiteCount != null ? (
                  <Typography sx={{ fontSize: "0.68rem", color: "rgba(129,140,248,0.85)" }}>
                    {t("graph.detailPanel.intCites", { count: String(selectedNode.internalCiteCount) })}
                  </Typography>
                ) : null}
                {selectedNode.externalCiteCount != null ? (
                  <Typography sx={{ fontSize: "0.68rem", color: "rgba(251,191,36,0.85)" }}>
                    {t("graph.detailPanel.extCites", { count: String(selectedNode.externalCiteCount) })}
                  </Typography>
                ) : null}
              </Box>
            ) : null}

            {onExpandWorkspaceNeighbors &&
            String(selectedNode.type) === "Work" &&
            Number(selectedNode.externalCiteCount) > 0 ? (
              <Box sx={{ mt: 1 }}>
                <CursorSmallButton
                  type="button"
                  disabled={expandWorkspaceNeighborsBusy}
                  onClick={() => onExpandWorkspaceNeighbors()}
                >
                  {expandWorkspaceNeighborsBusy
                    ? t("graph.detailPanel.loading")
                    : t("graph.detailPanel.expandExternal", { count: String(selectedNode.externalCiteCount) })}
                </CursorSmallButton>
              </Box>
            ) : null}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75 }}>
              {t("graph.detailPanel.keyProperties")}
            </Typography>
            {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mb: 1 }}>
                {Object.entries(selectedNode.properties).map(([k, v]) => (
                  <Box key={k} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "baseline" }}>
                    <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", minWidth: "7rem" }}>
                      {localizeWorkPropertyKey(k, t)}
                    </Typography>
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", flex: 1, wordBreak: "break-word" }}>
                      {formatPropertyValue(v)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.45)", mb: 1 }}>
                {t("graph.detailPanel.noProperties")}
              </Typography>
            )}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 1.5, mb: 0.75 }}>
              {t("graph.detailPanel.connections")}
            </Typography>
            {rows.length === 0 && relatedEdges.length === 0 ? (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>{t("graph.detailPanel.noEdges")}</Typography>
            ) : rows.length > 0 ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {rows.map(({ edge, otherLabel, readableLine, directionHint }) => {
                  const dirLabel = localizeDirectionHint(directionHint, t);
                  const dirTip = localizeDirectionHintTooltip(directionHint, t);
                  return (
                  <Box
                    key={edge.id}
                    component="button"
                    type="button"
                    onClick={() => {
                      onSelectNode?.("");
                      onSelectEdge?.(edge.id);
                    }}
                    sx={{
                      textAlign: "left",
                      cursor: "pointer",
                      p: 1,
                      borderRadius: "6px",
                      backgroundColor: "#141414",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "inherit",
                      font: "inherit",
                      "&:hover": {
                        borderColor: "rgba(99,102,241,0.35)",
                        backgroundColor: "rgba(99,102,241,0.06)",
                      },
                    }}
                  >
                    {dirTip ? (
                      <Tooltip title={dirTip} enterDelay={400} placement="top">
                        <Typography
                          component="span"
                          sx={{
                            display: "block",
                            fontSize: "0.68rem",
                            color: "rgba(255,255,255,0.42)",
                            cursor: "help",
                          }}
                        >
                          {dirLabel}
                        </Typography>
                      </Tooltip>
                    ) : (
                      <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.42)" }}>{dirLabel}</Typography>
                    )}
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap", mt: 0.25 }}>
                      <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.55)" }} aria-hidden />
                      <Chip
                        component="span"
                        size="small"
                        label={localizeEdgeType(edge, t)}
                        sx={{
                          height: 22,
                          fontSize: "0.7rem",
                          border: "1px solid rgba(129,140,248,0.35)",
                          backgroundColor: "rgba(99,102,241,0.12)",
                          color: "rgba(129,140,248,0.95)",
                          "& .MuiChip-label": { px: 0.75 },
                        }}
                      />
                    </Box>
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.86)", mt: 0.35, lineHeight: 1.4 }}>
                      → {otherLabel}
                    </Typography>
                    <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.48)", mt: 0.35, lineHeight: 1.35 }}>
                      {readableLine}
                    </Typography>
                  </Box>
                  );
                })}
              </Box>
            ) : (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {relatedEdges.map((edge) => (
                  <CursorSmallButton
                    key={edge.id}
                    type="button"
                    onClick={() => {
                      onSelectNode?.("");
                      onSelectEdge?.(edge.id);
                    }}
                    sx={{ justifyContent: "flex-start", textAlign: "left", height: "auto", py: 0.75, alignItems: "center", gap: 0.75 }}
                  >
                    <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.55)", flexShrink: 0 }} aria-hidden />
                    <Chip
                      component="span"
                      size="small"
                      label={localizeEdgeType(edge, t)}
                      sx={{
                        height: 22,
                        fontSize: "0.7rem",
                        border: "1px solid rgba(129,140,248,0.35)",
                        backgroundColor: "rgba(99,102,241,0.12)",
                        color: "rgba(129,140,248,0.95)",
                        flexShrink: 0,
                        verticalAlign: "middle",
                        "& .MuiChip-label": { px: 0.75 },
                      }}
                    />
                    <Typography component="span" sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.75)", textAlign: "left" }}>
                      {edge.source} → {edge.target}
                    </Typography>
                  </CursorSmallButton>
                ))}
              </Box>
            )}

            <Box sx={{ mt: 1.5 }}>
              <CursorSmallButton type="button" onClick={() => setRawOpen((v) => !v)} sx={{ mb: 0.5 }}>
                {rawOpen ? t("graph.detailPanel.hideAdvanced") : t("graph.detailPanel.showAdvanced")}
              </CursorSmallButton>
              {rawOpen ? (
                <Typography
                  component="pre"
                  sx={{
                    m: 0,
                    p: 1.25,
                    borderRadius: "6px",
                    backgroundColor: "#141414",
                    border: "1px solid rgba(255,255,255,0.06)",
                    fontSize: "0.72rem",
                    color: "rgba(255,255,255,0.65)",
                    overflow: "auto",
                    maxHeight: compact ? 200 : 280,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {JSON.stringify(selectedNode.raw && typeof selectedNode.raw === "object" ? selectedNode.raw : {}, null, 2)}
                </Typography>
              ) : null}
            </Box>
          </>
        ) : null}

        {selectedEdge ? (
          <Accordion
            disableGutters
            elevation={0}
            sx={{
              mt: 1.5,
              backgroundColor: "transparent",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: "6px",
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem", color: "rgba(255,255,255,0.5)" }} />}>
              <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.65)" }}>
                {t("graph.detailPanel.advancedJson")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Typography
                component="pre"
                sx={{
                  m: 0,
                  p: 1.25,
                  borderRadius: "6px",
                  backgroundColor: "#141414",
                  border: "1px solid rgba(255,255,255,0.06)",
                  fontSize: "0.72rem",
                  color: "rgba(255,255,255,0.65)",
                  overflow: "auto",
                  maxHeight: compact ? 200 : 280,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {JSON.stringify(selectedEdge.raw && typeof selectedEdge.raw === "object" ? selectedEdge.raw : {}, null, 2)}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ) : null}
      </Box>
    </Box>
  );
}
