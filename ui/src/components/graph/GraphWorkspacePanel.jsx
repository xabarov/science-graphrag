import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";

import { CursorSmallButton } from "../common/index.js";
import GraphVisualization from "./GraphVisualization.jsx";
import GraphCanvasMvp from "./GraphCanvasMvp.jsx";
import GraphDetailPanel from "./GraphDetailPanel.jsx";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "./graphShellStates.jsx";
import { fetchWorkGraphNormalized } from "./graphAdapter.js";
import { capGraphForUi } from "./graphUiLimits.js";
import { deriveGraphDetail, normalizeGraphNodeId, normalizeGraphPayload, resolveSelectedNodeId } from "./graphViewState.js";
import { describeTraceabilityState } from "../work/traceabilityState.js";

/**
 * @param {{
 *   workId: string,
 *   selectedNodeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   mode?: "embedded" | "standalone",
 *   title?: string,
 *   subtitle?: React.ReactNode,
 *   traceContext?: { chunkFingerprint?: string, section?: string, citation?: string },
 *   labMode?: boolean,
 * }} props
 */
export default function GraphWorkspacePanel({
  workId,
  selectedNodeId = "",
  onSelectNode,
  mode = "embedded",
  title = "Graph",
  subtitle = null,
  traceContext = {},
  labMode = false,
}) {
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [vizMode, setVizMode] = useState(/** @type {"cards" | "canvas"} */ ("cards"));
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(labMode);

  useEffect(() => {
    setDiagnosticsOpen(labMode);
  }, [labMode]);

  useEffect(() => {
    if (!workId.trim()) {
      setGraph(normalizeGraphPayload(null));
      setError(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const normalized = await fetchWorkGraphNormalized(workId);
        if (cancelled) return;
        setGraph(normalized);
      } catch (err) {
        if (cancelled) return;
        const msg = err?.response?.data?.detail
          ? JSON.stringify(err.response.data.detail)
          : err?.message || String(err);
        setError(msg);
        setGraph(normalizeGraphPayload(null));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  const resolvedSelectedNodeId = useMemo(
    () => resolveSelectedNodeId(graph, normalizeGraphNodeId(selectedNodeId)),
    [graph, selectedNodeId],
  );

  const { displayGraph, capWarnings } = useMemo(
    () => capGraphForUi(graph, resolvedSelectedNodeId),
    [graph, resolvedSelectedNodeId],
  );

  useEffect(() => {
    if (resolvedSelectedNodeId && resolvedSelectedNodeId !== normalizeGraphNodeId(selectedNodeId)) {
      onSelectNode?.(resolvedSelectedNodeId);
    }
  }, [onSelectNode, resolvedSelectedNodeId, selectedNodeId]);

  const detail = useMemo(() => deriveGraphDetail(graph, resolvedSelectedNodeId), [graph, resolvedSelectedNodeId]);
  const compact = mode === "embedded";
  const traceSummary = describeTraceabilityState(traceContext);

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography sx={{ fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
        {subtitle ? (
          typeof subtitle === "string" || typeof subtitle === "number" ? (
            <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)", mt: 0.5 }}>{subtitle}</Typography>
          ) : (
            <Box sx={{ mt: 0.5 }}>{subtitle}</Box>
          )
        ) : null}
      </Box>

      {!workId.trim() ? <GraphMissingWorkInline message="Pick a work to load graph context." /> : null}

      {loading ? <GraphLoadingInline /> : null}

      {error ? <GraphErrorAlert>{error}</GraphErrorAlert> : null}

      {!loading && !error && workId.trim() ? (
        <>
          {graph.warnings.length > 0 ? (
            <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.04)" }}>
              <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, mb: 0.5 }}>Graph data was normalized</Typography>
              <Box component="ul" sx={{ m: 0, pl: 2.25, mb: 0 }}>
                {graph.warnings.map((line, idx) => (
                  <Typography key={`graph-warn-${idx}`} component="li" sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
                    {line}
                  </Typography>
                ))}
              </Box>
            </Alert>
          ) : null}

          {capWarnings.length > 0 ? (
            <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem", backgroundColor: "rgba(99,102,241,0.08)" }}>
              <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600, mb: 0.5 }}>Large graph — UI cap</Typography>
              <Box component="ul" sx={{ m: 0, pl: 2.25, mb: 0 }}>
                {capWarnings.map((line, idx) => (
                  <Typography key={`graph-cap-${idx}`} component="li" sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.75)" }}>
                    {line}
                  </Typography>
                ))}
              </Box>
            </Alert>
          ) : null}

          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1.5 }}>
            <CursorSmallButton
              type="button"
              onClick={() => setVizMode("cards")}
              sx={
                vizMode === "cards"
                  ? {
                      backgroundColor: "rgba(99, 102, 241, 0.15)",
                      borderColor: "rgba(99, 102, 241, 0.3)",
                      color: "rgba(129,140,248,0.92)",
                    }
                  : {}
              }
            >
              Cards
            </CursorSmallButton>
            <CursorSmallButton
              type="button"
              onClick={() => setVizMode("canvas")}
              sx={
                vizMode === "canvas"
                  ? {
                      backgroundColor: "rgba(99, 102, 241, 0.15)",
                      borderColor: "rgba(99, 102, 241, 0.3)",
                      color: "rgba(129,140,248,0.92)",
                    }
                  : {}
              }
            >
              Graph
            </CursorSmallButton>
          </Box>

          <GraphTypeLegend graph={displayGraph} />

          <Box
            sx={{
              display: "grid",
              gap: 2,
              minHeight: { xs: "auto", md: compact ? 420 : 520 },
              gridTemplateColumns: {
                xs: "minmax(0, 1fr)",
                md: compact ? "minmax(0, 1.7fr) minmax(280px, 1fr)" : "minmax(0, 2fr) minmax(320px, 1fr)",
              },
              alignItems: "stretch",
            }}
          >
            <Box
              sx={{
                minWidth: 0,
                minHeight: { xs: 280, md: compact ? 400 : 500 },
                display: "flex",
                flexDirection: "column",
                alignSelf: "stretch",
                height: "100%",
              }}
            >
              {vizMode === "cards" ? (
                <GraphVisualization
                  graph={displayGraph}
                  selectedNodeId={resolvedSelectedNodeId}
                  onSelectNode={(nodeId) => onSelectNode?.(nodeId)}
                  mode={mode}
                />
              ) : (
                <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                  <GraphCanvasMvp
                    graph={displayGraph}
                    selectedNodeId={resolvedSelectedNodeId}
                    onSelectNode={(nodeId) => onSelectNode?.(nodeId)}
                  />
                </Box>
              )}
            </Box>
            <Box sx={{ minWidth: 0, minHeight: { xs: 220, md: compact ? 400 : 500 }, display: "flex", flexDirection: "column" }}>
              <GraphDetailPanel selectedNode={detail.selectedNode} relatedEdges={detail.relatedEdges} mode={mode} />
            </Box>
          </Box>

          <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Box sx={{ px: 1, py: 0.5, borderRadius: "999px", backgroundColor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>nodes: {graph.nodeCount}</Typography>
            </Box>
            <Box sx={{ px: 1, py: 0.5, borderRadius: "999px", backgroundColor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>edges: {graph.edgeCount}</Typography>
            </Box>
            <Tooltip
              title={
                graph.meta?.semantic_available
                  ? "This work has Method/Dataset links in Neo4j (USES_METHOD / EVALUATED_ON from semantic extraction)."
                  : "No Method/Dataset layer for this work yet. That is normal if semantic extraction was off, the LLM key was missing, or confidence stayed below the graph threshold."
              }
              placement="top"
              enterDelay={400}
            >
              <Box
                component="span"
                sx={{
                  display: "inline-flex",
                  px: 1,
                  py: 0.5,
                  borderRadius: "999px",
                  backgroundColor: "rgba(99, 102, 241, 0.1)",
                  border: "1px solid rgba(99, 102, 241, 0.25)",
                  cursor: "help",
                }}
              >
                <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.92)" }}>
                  semantic_available: {String(Boolean(graph.meta?.semantic_available))}
                </Typography>
              </Box>
            </Tooltip>
          </Box>

          {traceSummary.length > 0 ? (
            <Alert severity="info" sx={{ mt: 2, fontSize: "0.8125rem", backgroundColor: "rgba(99,102,241,0.08)" }}>
              Opened from traceability context: {traceSummary.join(" · ")}
            </Alert>
          ) : null}

          {graph.nodeCount === 0 ? (
            <Alert severity="info" sx={{ mt: 2, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.04)" }}>
              This response has no nodes yet—try another work_id or confirm the work has graph data (empty neighborhood is normal for some works).
            </Alert>
          ) : null}

          <Box sx={{ mt: 2 }}>
            {!labMode ? (
              <CursorSmallButton type="button" onClick={() => setDiagnosticsOpen((o) => !o)} sx={{ mb: 1 }}>
                {diagnosticsOpen ? "Hide diagnostics" : "Show diagnostics"}
              </CursorSmallButton>
            ) : (
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.85)", mb: 1 }}>Graph Lab: diagnostics expanded</Typography>
            )}
            <Collapse in={labMode || diagnosticsOpen}>
              <Box sx={{ p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
                <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.75 }}>Diagnostics JSON</Typography>
                <Typography
                  component="pre"
                  sx={{
                    m: 0,
                    fontSize: "0.75rem",
                    color: "rgba(255,255,255,0.6)",
                    overflow: "auto",
                    maxHeight: compact ? 180 : 240,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {JSON.stringify(
                    {
                      work_id: graph.workId,
                      meta: graph.meta,
                      selected_node_id: resolvedSelectedNodeId,
                      node_count: graph.nodeCount,
                      edge_count: graph.edgeCount,
                      warnings: graph.warnings,
                      ui_cap_warnings: capWarnings,
                    },
                    null,
                    2,
                  )}
                </Typography>
              </Box>
            </Collapse>
          </Box>
        </>
      ) : null}
    </Box>
  );
}
