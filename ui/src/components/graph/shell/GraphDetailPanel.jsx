import React from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../../i18n/useI18n.js";
import GraphEdgeDetailSection from "./detail/GraphEdgeDetailSection.jsx";
import GraphNodeDetailSection from "./detail/GraphNodeDetailSection.jsx";
import { useGraphContradictionDetail } from "./detail/useGraphContradictionDetail.js";
import { graphContractSubtitle } from "./graphContractSubtitle.js";

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
 *   workspaceId?: string,
 * }} props
 */
export default function GraphDetailPanel({
  workspaceId = "",
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
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  const effectiveWorkspaceId = String(workspaceId || "").trim() || String(graphMeta?.workspace_id || "").trim();
  const isContradictsEdge = Boolean(selectedEdge) && String(selectedEdge?.type || "").toUpperCase() === "CONTRADICTS";

  const { contradictionPayload, contradictionBusy, contradictionError } = useGraphContradictionDetail({
    effectiveWorkspaceId,
    isContradictsEdge,
    selectedEdge,
    t,
  });

  const truncated = Boolean(graphMeta?.is_truncated);
  const neighborLimit = graphMeta?.neighbor_limit_applied;
  const neighborCount = graphMeta?.neighbor_match_count;
  const truncatedLimitClause =
    neighborLimit != null ? t("graph.detailPanel.truncatedLimitClause", { neighborLimit: String(neighborLimit) }) : "";
  const contractLine = graphContractSubtitle(graphMeta, t);

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
      <Typography
        component="h2"
        sx={{
          fontWeight: 600,
          fontSize: "0.8125rem",
          mb: contractLine ? 0.5 : 1,
          flexShrink: 0,
          color: tk.text.primary,
        }}
      >
        {t("graph.detailPanel.title")}
      </Typography>
      {contractLine ? (
        <Typography
          sx={{
            fontSize: "0.75rem",
            color: tk.text.secondary,
            lineHeight: 1.45,
            mb: 1,
            flexShrink: 0,
          }}
        >
          {contractLine}
        </Typography>
      ) : null}

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
          <GraphEdgeDetailSection
            tk={tk}
            t={t}
            selectedEdge={selectedEdge}
            selectedEdgeReadable={selectedEdgeReadable}
            isContradictsEdge={isContradictsEdge}
            onSelectNode={onSelectNode}
            contradictionPayload={contradictionPayload}
            contradictionBusy={contradictionBusy}
            contradictionError={contradictionError}
            effectiveWorkspaceId={effectiveWorkspaceId}
          />
        ) : null}

        {selectedNode ? (
          <GraphNodeDetailSection
            tk={tk}
            t={t}
            selectedNode={selectedNode}
            relatedEdges={relatedEdges}
            relatedEdgeRows={rows}
            authorAuthoredWorks={authorAuthoredWorks}
            compact={compact}
            onSelectNode={onSelectNode}
            onSelectEdge={onSelectEdge}
            onExpandWorkspaceNeighbors={onExpandWorkspaceNeighbors}
            onAggregatorExpand={onAggregatorExpand}
            expandWorkspaceNeighborsBusy={expandWorkspaceNeighborsBusy}
          />
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
