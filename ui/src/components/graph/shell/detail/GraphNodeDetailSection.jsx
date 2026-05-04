import React, { useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { CursorSmallButton } from "../../../common/index.js";
import MarkdownViewCore from "../../../work/markdown/MarkdownViewCore.jsx";
import {
  localizeAggregatorSubtitle,
  localizeAggregatorTitle,
  localizeClaimPropertyKey,
  localizeMethodPropertyKey,
  localizeNodeKind,
  localizeWorkPropertyKey,
} from "../../model/graphLocalize.js";
import {
  CLAIM_DETAIL_KEYS_IN_TABLE,
  METHOD_DETAIL_KEYS_IN_TABLE,
  claimBodyFromProperties,
  formatClaimMetadataBlock,
  formatPropertyValue,
  isClaimSelectedNode,
} from "./detailFormatters.js";
import NodeConnectionsList from "./NodeConnectionsList.jsx";

/**
 * @param {{
 *   tk: import("@mui/material/styles").Theme["appTokens"],
 *   t: (k: string, opts?: object) => string,
 *   selectedNode: object,
 *   relatedEdges: Array<object>,
 *   relatedEdgeRows: Array<object>,
 *   authorAuthoredWorks: Array<object>,
 *   compact: boolean,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 *   onExpandWorkspaceNeighbors?: () => void | Promise<void>,
 *   onAggregatorExpand?: (node: object, expandEndpoint: string) => void | Promise<void>,
 *   expandWorkspaceNeighborsBusy?: boolean,
 * }} props
 */
export default function GraphNodeDetailSection({
  tk,
  t,
  selectedNode,
  relatedEdges,
  relatedEdgeRows,
  authorAuthoredWorks,
  compact,
  onSelectNode,
  onSelectEdge,
  onExpandWorkspaceNeighbors,
  onAggregatorExpand,
  expandWorkspaceNeighborsBusy = false,
}) {
  const [rawOpen, setRawOpen] = useState(false);
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  const claimNode = isClaimSelectedNode(selectedNode);
  const claimProps =
    claimNode && selectedNode?.properties && typeof selectedNode.properties === "object"
      ? /** @type {Record<string, unknown>} */ (selectedNode.properties)
      : null;
  const claimBody = claimProps ? claimBodyFromProperties(claimProps) : "";
  const claimMetadataFormatted = claimProps ? formatClaimMetadataBlock(claimProps.claim_metadata) : "";
  const isMethodNode = Boolean(selectedNode && String(selectedNode.type) === "Method");
  const methodProps =
    isMethodNode && selectedNode?.properties && typeof selectedNode.properties === "object"
      ? /** @type {Record<string, unknown>} */ (selectedNode.properties)
      : null;
  const methodMarkdownForViewer = methodProps
    ? String(methodProps.description_markdown || "").trim() ||
      String(methodProps.description_plaintext || "").trim() ||
      String(methodProps.description_short || "").trim()
    : "";
  const excludedDetailKeys = claimNode ? CLAIM_DETAIL_KEYS_IN_TABLE : isMethodNode ? METHOD_DETAIL_KEYS_IN_TABLE : new Set();
  const detailPropertyEntries = Object.entries(selectedNode?.properties || {}).filter(([k]) => !excludedDetailKeys.has(k));

  return (
    <>
      {String(selectedNode.nodeKind) === "Aggregator" ? (
        <Box sx={{ mb: 1.5 }}>
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>{t("graph.aggregator.badge")}</Typography>
          <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25 }}>
            {localizeAggregatorTitle(selectedNode, t)}
          </Typography>
          <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>{localizeAggregatorSubtitle(t)}</Typography>
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
            onClick={() => onAggregatorExpand?.(selectedNode, String(selectedNode.raw?.aggregation_hints?.expand_endpoint || ""))}
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
          <Typography sx={{ fontSize: "0.7rem", color: tk.text.accent }}>{localizeNodeKind(selectedNode, t)}</Typography>
          <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: tk.text.primary, mt: 0.25, lineHeight: 1.35 }}>
            {selectedNode.displayLabel || selectedNode.label}
          </Typography>
          {selectedNode.subtitle ? (
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mt: 0.35 }}>{selectedNode.subtitle}</Typography>
          ) : null}
        </>
      ) : null}

      {String(selectedNode.type) === "Work" &&
      (selectedNode.workspaceMembership || selectedNode.internalCiteCount != null || selectedNode.externalCiteCount != null) ? (
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

      {onExpandWorkspaceNeighbors && String(selectedNode.type) === "Work" && Number(selectedNode.externalCiteCount) > 0 ? (
        <Box sx={{ mt: 1 }}>
          <CursorSmallButton type="button" disabled={expandWorkspaceNeighborsBusy} onClick={() => onExpandWorkspaceNeighbors()}>
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
                  <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, minWidth: 0 }}>{row.workLabel}</Typography>
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
                  <Typography sx={{ fontSize: "0.72rem", color: tk.text.accent }}>{t("graph.detailPanel.authorCorresponding")}</Typography>
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

      {isMethodNode && methodMarkdownForViewer ? (
        <Box sx={{ mt: 2, mb: 1 }}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5, color: tk.text.primary }}>
            {t("graph.detailPanel.methodDescription")}
          </Typography>
          <Box
            sx={{
              p: 1,
              borderRadius: "6px",
              border: `1px solid ${tk.border.default}`,
              backgroundColor: tk.surface.sidebar,
              maxHeight: compact ? 260 : 360,
              overflow: "auto",
            }}
          >
            <MarkdownViewCore markdown={methodMarkdownForViewer} data-testid="graph-method-markdown" />
          </Box>
        </Box>
      ) : null}

      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75, color: tk.text.primary }}>
        {t("graph.detailPanel.keyProperties")}
      </Typography>
      {detailPropertyEntries.length > 0 ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mb: 1 }}>
          {detailPropertyEntries.map(([k, v]) => (
            <Box key={k} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "baseline" }}>
              <Typography sx={{ fontSize: "0.72rem", color: tk.text.muted, minWidth: "7rem" }}>
                {claimNode ? localizeClaimPropertyKey(k, t) : isMethodNode ? localizeMethodPropertyKey(k, t) : localizeWorkPropertyKey(k, t)}
              </Typography>
              <Typography sx={{ fontSize: "0.8125rem", color: tk.text.primary, flex: 1, wordBreak: "break-word" }}>
                {formatPropertyValue(v)}
              </Typography>
            </Box>
          ))}
        </Box>
      ) : (
        <Typography sx={{ fontSize: "0.8125rem", color: tk.text.muted, mb: 1 }}>{t("graph.detailPanel.noProperties")}</Typography>
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
      <NodeConnectionsList tk={tk} t={t} rows={rows} relatedEdges={relatedEdges} onSelectEdge={onSelectEdge} />

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
  );
}
