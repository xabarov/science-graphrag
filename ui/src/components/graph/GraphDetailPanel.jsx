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
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { CursorSmallButton } from "../common/index.js";

/**
 * @param {Record<string, unknown>} props
 */
function formatPropertyLabel(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * @param {unknown} v
 */
function formatPropertyValue(v) {
  if (v == null) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
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
  const compact = mode === "embedded" || mode === "standalone";
  const [rawOpen, setRawOpen] = useState(false);
  const rows = relatedEdgeRows.length > 0 ? relatedEdgeRows : [];

  const truncated = Boolean(graphMeta?.is_truncated);
  const neighborLimit = graphMeta?.neighbor_limit_applied;
  const neighborCount = graphMeta?.neighbor_match_count;

  return (
    <Box
      component="aside"
      role="region"
      aria-label="Graph details"
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
        Details
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
            Neighborhood is truncated for performance ({neighborCount != null ? String(neighborCount) : "?"} relationships
            {neighborLimit != null ? `, showing up to ${neighborLimit}` : ""}). Increase{" "}
            <Typography component="span" sx={{ fontFamily: "monospace", fontSize: "0.72rem" }}>
              neighbor_limit
            </Typography>{" "}
            on the API query if you need more.
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
          {mode === "standalone"
            ? "Click a node or edge on the canvas. Raw JSON: Advanced."
            : "Select a node or an edge on the graph to see a readable summary. Technical JSON stays under \"Advanced\"."}
        </Typography>
      ) : null}

      <Box sx={{ flex: 1, minHeight: 0, overflow: "auto", pr: 0.25 }}>
        {selectedEdge ? (
          <>
            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>Relationship</Typography>
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.88)", lineHeight: 1.45, mb: 1 }}>
              {selectedEdgeReadable ||
                `${selectedEdge.sourceLabel || selectedEdge.source} —[${selectedEdge.displayType || selectedEdge.type}]→ ${selectedEdge.targetLabel || selectedEdge.target}`}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.9)", mb: 0.5 }}>
              {selectedEdge.displayType || String(selectedEdge.type || "").replace(/_/g, " ") || "related"}
            </Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, mb: 1 }}>
              <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.source)}>Open source</CursorSmallButton>
              <CursorSmallButton type="button" onClick={() => onSelectNode?.(selectedEdge.target)}>Open target</CursorSmallButton>
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
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.92)" }}>Aggregator</Typography>
                <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", mt: 0.25 }}>
                  {selectedNode.displayLabel || selectedNode.label}
                </Typography>
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mt: 0.35 }}>
                  {String(selectedNode.raw?.aggregation_hints?.aggregator_kind || "").replace(/_/g, " ")}
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
                    ? "Loading…"
                    : `Expand all (${String(selectedNode.raw?.aggregation_hints?.count || 0)})`}
                </CursorSmallButton>
              </Box>
            ) : null}
            <Typography sx={{ fontSize: "0.7rem", color: "rgba(129,140,248,0.92)" }}>
              {selectedNode.nodeKind || selectedNode.type}
            </Typography>
            <Typography sx={{ fontSize: "0.9375rem", fontWeight: 600, color: "rgba(255,255,255,0.9)", mt: 0.25, lineHeight: 1.35 }}>
              {selectedNode.displayLabel || selectedNode.label}
            </Typography>
            {selectedNode.subtitle ? (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", mt: 0.35 }}>{selectedNode.subtitle}</Typography>
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
                    int cites: {String(selectedNode.internalCiteCount)}
                  </Typography>
                ) : null}
                {selectedNode.externalCiteCount != null ? (
                  <Typography sx={{ fontSize: "0.68rem", color: "rgba(251,191,36,0.85)" }}>
                    ext cites: {String(selectedNode.externalCiteCount)}
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
                    ? "Loading…"
                    : `Expand external neighborhood (+${String(selectedNode.externalCiteCount)})`}
                </CursorSmallButton>
              </Box>
            ) : null}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 2, mb: 0.75 }}>Key properties</Typography>
            {selectedNode.properties && Object.keys(selectedNode.properties).length > 0 ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5, mb: 1 }}>
                {Object.entries(selectedNode.properties).map(([k, v]) => (
                  <Box key={k} sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, alignItems: "baseline" }}>
                    <Typography sx={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", minWidth: "7rem" }}>
                      {formatPropertyLabel(k)}
                    </Typography>
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.82)", flex: 1, wordBreak: "break-word" }}>
                      {formatPropertyValue(v)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.45)", mb: 1 }}>No structured properties on this node.</Typography>
            )}

            <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mt: 1.5, mb: 0.75 }}>Connections</Typography>
            {rows.length === 0 && relatedEdges.length === 0 ? (
              <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No connected edges in the current view.</Typography>
            ) : rows.length > 0 ? (
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {rows.map(({ edge, otherLabel, readableLine, directionHint }) => (
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
                    <Typography sx={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.42)", textTransform: "lowercase" }}>
                      {directionHint}
                    </Typography>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap", mt: 0.25 }}>
                      <ArrowForwardIcon sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.55)" }} aria-hidden />
                      <Chip
                        component="span"
                        size="small"
                        label={edge.displayType || String(edge.type || "").replace(/_/g, " ") || "—"}
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
                ))}
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
                      label={edge.displayType || edge.type || "—"}
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
                {rawOpen ? "Hide" : "Show"} advanced (raw JSON)
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
              <Typography sx={{ fontSize: "0.75rem", fontWeight: 600, color: "rgba(255,255,255,0.65)" }}>Advanced (raw JSON)</Typography>
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
