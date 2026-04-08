import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";

import { getWorkGraph } from "../../services/researchApi.js";
import GraphVisualization from "./GraphVisualization.jsx";
import GraphDetailPanel from "./GraphDetailPanel.jsx";
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
}) {
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

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
        const res = await getWorkGraph(workId);
        if (cancelled) return;
        setGraph(normalizeGraphPayload(res.data));
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
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)", mt: 0.5 }}>{subtitle}</Typography>
        ) : null}
      </Box>

      {!workId.trim() ? (
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Pick a work to load graph context.</Typography>
      ) : null}

      {loading ? (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2 }}>
          <CircularProgress size={22} sx={{ color: "rgba(129,140,248,0.9)" }} />
          <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>Loading graph…</Typography>
        </Box>
      ) : null}

      {error ? (
        <Alert severity="error" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {error}
        </Alert>
      ) : null}

      {!loading && !error && workId.trim() ? (
        <>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: compact ? "minmax(0, 1.7fr) minmax(280px, 1fr)" : "minmax(0, 2fr) minmax(320px, 1fr)",
              alignItems: "start",
            }}
          >
            <GraphVisualization graph={graph} selectedNodeId={resolvedSelectedNodeId} onSelectNode={(nodeId) => onSelectNode?.(nodeId)} mode={mode} />
            <GraphDetailPanel selectedNode={detail.selectedNode} relatedEdges={detail.relatedEdges} mode={mode} />
          </Box>

          <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1 }}>
            <Box sx={{ px: 1, py: 0.5, borderRadius: "999px", backgroundColor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>nodes: {graph.nodeCount}</Typography>
            </Box>
            <Box sx={{ px: 1, py: 0.5, borderRadius: "999px", backgroundColor: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>edges: {graph.edgeCount}</Typography>
            </Box>
            <Box sx={{ px: 1, py: 0.5, borderRadius: "999px", backgroundColor: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.25)" }}>
              <Typography sx={{ fontSize: "0.75rem", color: "rgba(129,140,248,0.92)" }}>
                semantic_available: {String(Boolean(graph.meta?.semantic_available))}
              </Typography>
            </Box>
          </Box>

          {traceSummary.length > 0 ? (
            <Alert severity="info" sx={{ mt: 2, fontSize: "0.8125rem", backgroundColor: "rgba(99,102,241,0.08)" }}>
              Opened from traceability context: {traceSummary.join(" · ")}
            </Alert>
          ) : null}

          {graph.nodeCount === 0 ? (
            <Alert severity="info" sx={{ mt: 2, fontSize: "0.8125rem", backgroundColor: "rgba(255,255,255,0.04)" }}>
              Graph payload loaded but does not contain nodes yet.
            </Alert>
          ) : null}

          <Box sx={{ mt: 2, p: 1.5, borderRadius: "6px", border: "1px solid rgba(255,255,255,0.08)", backgroundColor: "#141414" }}>
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
                },
                null,
                2,
              )}
            </Typography>
          </Box>
        </>
      ) : null}
    </Box>
  );
}
