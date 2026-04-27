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
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";
import { CursorSmallButton } from "../common/index.js";
import {
  localizeAggregatorSubtitle,
  localizeAggregatorTitle,
  localizeClaimPropertyKey,
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

/** @param {{ type?: string } | null | undefined} node */
function isClaimSelectedNode(node) {
  return Boolean(node && String(node.type) === "Claim");
}

/** @param {Record<string, unknown>} props */
function claimBodyFromProperties(props) {
  const norm = props?.normalized_text;
  const raw = props?.text;
  const n = typeof norm === "string" ? norm.trim() : norm != null ? String(norm).trim() : "";
  if (n) return n;
  const t = typeof raw === "string" ? raw.trim() : raw != null ? String(raw).trim() : "";
  return t || "";
}

/** @param {unknown} meta */
function formatClaimMetadataBlock(meta) {
  if (meta == null || meta === "") return "";
  if (typeof meta === "string") {
    const s = meta.trim();
    if (!s) return "";
    try {
      return JSON.stringify(JSON.parse(s), null, 2);
    } catch {
      return s;
    }
  }
  if (typeof meta === "object") return JSON.stringify(meta, null, 2);
  return String(meta);
}

/** Claim fields rendered in dedicated blocks; rest stays in the key table with i18n labels. */
const CLAIM_DETAIL_KEYS_IN_TABLE = new Set(["normalized_text", "text", "claim_metadata"]);

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
 *   authorAuthoredWorks?: Array<{ workId: string, workLabel: string, authorPosition: unknown, isCorresponding: unknown, rawAffiliation: unknown }>,
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
  authorAuthoredWorks = [],
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
  const tk = useTheme().appTokens;
  const compact = mode === "embedded" || mode === "standalone";
  const [rawOpen, setRawOpen] = useState(false);
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  const claimNode = isClaimSelectedNode(selectedNode);
  const claimProps =
    claimNode && selectedNode?.properties && typeof selectedNode.properties === "object"
      ? /** @type {Record<string, unknown>} */ (selectedNode.properties)
      : null;
  const claimBody = claimProps ? claimBodyFromProperties(claimProps) : "";
  const claimMetadataFormatted = claimProps ? formatClaimMetadataBlock(claimProps.claim_metadata) : "";
  const claimPropertyEntries = claimNode
    ? Object.entries(selectedNode?.properties || {}).filter(([k]) => !CLAIM_DETAIL_KEYS_IN_TABLE.has(k))
    : Object.entries(selectedNode?.properties || {});

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
        border: `1px solid ${tk.border.default}`,
        backgroundColor: tk.surface.panel,
        p: compact ? 1.5 : 2,
        flex: 1,
        minHeight: mode === "standalone" ? 0 : compact ? 280 : 360,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Typography component="h2" sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 1, flexShrink: 0, color: tk.text.primary }}>
        {t("graph.detailPanel.title")}
      </Typography>

      {truncated ? (
        <Box
          sx={{
            mb: 1,
            p: 1,
            borderRadius: "6px",
            border: `1px solid ${tk.accent.softBorder}`,
            backgroundColor: tk.accent.softBg,
            flexShrink: 0,
          }}
        >
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.primary, lineHeight: 1.45 }}>
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
            color: tk.text.muted,
            lineHeight: 1.4,
          }}
        >
          {mode === "standalone" ? t("graph.detailPanel.emptyStandalone") : t("graph.detailPanel.emptyEmbedded")}
        </Typography>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.25 }}>
        {selectedEdge ? (
          <>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>{t("graph.detailPanel.relationship")}</Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, lineHeight: 1.45, mb: 1 }}>
              {selectedEdgeReadable ||
                `${selectedEdge.sourceLabel || selectedEdge.source} —[${localizeEdgeType(selectedEdge, t)}]→ ${selectedEdge.targetLabel || selectedEdge.target}`}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent, mb: 0.5 }}>
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
            <Typography sx={{ fontSize: "0.7rem", color: tk.text.faint, fontFamily: "monospace", wordBreak: "break-all" }}>
              id: {selectedEdge.id}
            </Typography>
          </>
        ) : null}

        {selectedNode ? (
          <>
            {String(selectedNode.nodeKind) === "Aggregator" ? (
              <Box sx={{ mb: 1.5 }}>
                <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>{t("graph.aggregator.badge")}</Typography>
                <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25 }}>
                  {localizeAggregatorTitle(selectedNode, t)}
                </Typography>
                <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>
                  {localizeAggregatorSubtitle(t)}
                </Typography>
                {Array.isArray(selectedNode.raw?.aggregation_hints?.preview_labels) &&
                selectedNode.raw.aggregation_hints.preview_labels.length > 0 ? (
                  <List dense sx={{ py: 0.5 }}>
                    {selectedNode.raw.aggregation_hints.preview_labels.map((label) => (
                      <ListItem key={String(label)} sx={{ px: 0 }}>
                        <ListItemText primary={String(label)} primaryTypographyProps={{ sx: { color: tk.text.primary } }} />
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
                <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>
                  {localizeNodeKind(selectedNode, t)}
                </Typography>
                <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25, lineHeight: 1.35 }}>
                  {selectedNode.displayLabel || selectedNode.label}
                </Typography>
                {selectedNode.subtitle ? (
                  <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>{selectedNode.subtitle}</Typography>
                ) : null}
              </>
            ) : null}

            {String(selectedNode.type) === "Work" &&
            (selectedNode.workspaceMembership ||
              selectedNode.internalCiteCount != null ||
              selectedNode.externalCiteCount != null) ? (
              <Box sx={{ mt: 1, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
                {selectedNode.workspaceMembership ? (
                  <Typography sx={{ fontSize: "0.68rem", color: tk.text.muted, fontFamily: "monospace" }}>
                    {String(selectedNode.workspaceMembership)}
                  </Typography>
                ) : null}
                {selectedNode.internalCiteCount != null ? (
                  <Typography sx={{ fontSize: "0.68rem", color: tk.text.accent }}>
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

            {selectedNode &&
            (String(selectedNode.type) === "Author" || String(selectedNode.nodeKind) === "Author") &&
            authorAuthoredWorks.length > 0 ? (
              <Box sx={{ mt: 2 }}>
                <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.75, color: tk.text.primary }}>
                  {t("graph.detailPanel.authorWorks")}
                </Typography>
                <List dense sx={{ py: 0, maxHeight: compact ? 200 : 260, overflow: "auto" }}>
                  {authorAuthoredWorks.map((row) => (
                    <ListItem
                      key={row.workId}
                      sx={{
                        px: 0,
                        py: 0.75,
                        alignItems: "flex-start",
                        flexDirection: "column",
                        gap: 0.5,
                        borderBottom: `1px solid ${tk.border.default}`,
                      }}
                    >
                      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75, width: "100%" }}>
                        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, minWidth: 0 }}>
                          {row.workLabel}
                        </Typography>
                        <CursorSmallButton type="button" onClick={() => onSelectNode?.(row.workId)}>
                          {t("graph.detailPanel.authorWorkOpen")}
                        </CursorSmallButton>
                      </Box>
                      {row.authorPosition != null && String(row.authorPosition).trim() !== "" ? (
                        <Typography sx={{ fontSize: "0.72rem", color: tk.text.secondary }}>
                          {t("graph.detailPanel.authorPosition", { position: String(row.authorPosition) })}
                        </Typography>
                      ) : null}
                      {row.isCorresponding === true || row.isCorresponding === "true" ? (
                        <Typography sx={{ fontSize: "0.72rem", color: tk.text.accent }}>
                          {t("graph.detailPanel.authorCorresponding")}
                        </Typography>
                      ) : null}
                      {row.rawAffiliation != null && String(row.rawAffiliation).trim() !== "" ? (
                        <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, lineHeight: 1.4 }}>
                          {t("graph.detailPanel.authorAffiliation")}: {String(row.rawAffiliation)}
                        </Typography>
                      ) : null}
                    </ListItem>
                  ))}
                </List>
              </Box>
            ) : null}

            {claimNode && claimBody ? (
              <Box sx={{ mt: 2, mb: 1 }}>
                <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>
                  {t("graph.detailPanel.claimBody")}
                </Typography>
                <Typography
                  component="div"
                  sx={{
                    fontSize: "0.8125rem",
                    color: tk.text.primary,
                    lineHeight: 1.45,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    p: 1,
                    borderRadius: "6px",
                    border: `1px solid ${tk.border.default}`,
                    backgroundColor: tk.surface.sidebar,
                    maxHeight: compact ? 220 : 320,
                    overflow: "auto",
                  }}
                >
                  {claimBody}
                </Typography>
              </Box>
            ) : null}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75, color: tk.text.primary }}>
              {t("graph.detailPanel.keyProperties")}
            </Typography>
            {claimPropertyEntries.length > 0 ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mb: 1 }}>
                {claimPropertyEntries.map(([k, v]) => (
                  <Box key={k} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "baseline" }}>
                    <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, minWidth: "7rem" }}>
                      {claimNode ? localizeClaimPropertyKey(k, t) : localizeWorkPropertyKey(k, t)}
                    </Typography>
                    <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, wordBreak: "break-word" }}>
                      {formatPropertyValue(v)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1 }}>
                {t("graph.detailPanel.noProperties")}
              </Typography>
            )}

            {claimNode && claimMetadataFormatted ? (
              <Accordion
                disableGutters
                elevation={0}
                sx={{
                  mb: 1,
                  backgroundColor: "transparent",
                  border: `1px solid ${tk.border.default}`,
                  borderRadius: "6px",
                  "&:before": { display: "none" },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem", color: tk.text.muted }} />}>
                  <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
                    {t("graph.detailPanel.claimMetadataTitle")}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ pt: 0 }}>
                  <Typography
                    component="pre"
                    sx={{
                      m: 0,
                      p: 1.25,
                      borderRadius: "6px",
                      backgroundColor: tk.surface.code,
                      border: `1px solid ${tk.border.default}`,
                      fontSize: "0.72rem",
                      color: tk.text.secondary,
                      overflow: "auto",
                      maxHeight: compact ? 200 : 280,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {claimMetadataFormatted}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ) : null}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 1.5, mb: 0.75, color: tk.text.primary }}>
              {t("graph.detailPanel.connections")}
            </Typography>
            {rows.length === 0 && relatedEdges.length === 0 ? (
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted }}>{t("graph.detailPanel.noEdges")}</Typography>
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
                    onClick={() => onSelectEdge?.(edge.id)}
                    sx={{
                      textAlign: "left",
                      cursor: "pointer",
                      p: 1,
                      borderRadius: "6px",
                      backgroundColor: tk.surface.sidebar,
                      border: `1px solid ${tk.border.default}`,
                      color: "inherit",
                      font: "inherit",
                      "&:hover": {
                        borderColor: tk.accent.emphasisHoverBorder,
                        backgroundColor: tk.accent.softBg,
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
                            color: tk.text.faint,
                            cursor: "help",
                          }}
                        >
                          {dirLabel}
                        </Typography>
                      </Tooltip>
                    ) : (
                      <Typography sx={{ fontSize: "0.68rem", color: tk.text.faint }}>{dirLabel}</Typography>
                    )}
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap", mt: 0.25 }}>
                      <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: tk.text.accent }} aria-hidden />
                      <Chip
                        component="span"
                        size="small"
                        label={localizeEdgeType(edge, t)}
                        sx={{
                          height: 22,
                          fontSize: "0.7rem",
                          border: `1px solid ${tk.accent.softBorder}`,
                          backgroundColor: tk.accent.chipReadyBg,
                          color: tk.accent.chipReadyFg,
                          "& .MuiChip-label": { px: 0.75 },
                        }}
                      />
                    </Box>
                    <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, mt: 0.35, lineHeight: 1.4 }}>
                      → {otherLabel}
                    </Typography>
                    <Typography sx={{ fontSize: "0.7rem", color: tk.text.secondary, mt: 0.35, lineHeight: 1.35 }}>
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
                    onClick={() => onSelectEdge?.(edge.id)}
                    sx={{ justifyContent: "flex-start", textAlign: "left", height: "auto", py: 0.75, alignItems: "center", gap: 0.75 }}
                  >
                    <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: tk.text.accent, flexShrink: 0 }} aria-hidden />
                    <Chip
                      component="span"
                      size="small"
                      label={localizeEdgeType(edge, t)}
                      sx={{
                        height: 22,
                        fontSize: "0.7rem",
                        border: `1px solid ${tk.accent.softBorder}`,
                        backgroundColor: tk.accent.chipReadyBg,
                        color: tk.accent.chipReadyFg,
                        flexShrink: 0,
                        verticalAlign: "middle",
                        "& .MuiChip-label": { px: 0.75 },
                      }}
                    />
                    <Typography component="span" sx={{ fontSize: "0.75rem", color: tk.text.secondary, textAlign: "left" }}>
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
                    backgroundColor: tk.surface.code,
                    border: `1px solid ${tk.border.default}`,
                    fontSize: "0.72rem",
                    color: tk.text.secondary,
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
              border: `1px solid ${tk.border.default}`,
              borderRadius: "6px",
              "&:before": { display: "none" },
            }}
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ fontSize: "1rem", color: tk.text.muted }} />}>
              <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: tk.text.secondary }}>
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
                  backgroundColor: tk.surface.code,
                  border: `1px solid ${tk.border.default}`,
                  fontSize: "0.72rem",
                  color: tk.text.secondary,
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
