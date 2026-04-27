import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import { useI18n } from "../../i18n/useI18n.js";
import { describeTraceabilityState } from "../work/traceabilityState.js";
import GraphCanvasMvp from "./GraphCanvasMvp.jsx";
import GraphDebugInspector from "./GraphDebugInspector.jsx";
import GraphFlowView from "./GraphFlowView.jsx";
import GraphSidePanel from "./GraphSidePanel.jsx";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import GraphViewModeSwitch from "./GraphViewModeSwitch.jsx";
import GraphVisualization from "./GraphVisualization.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "./graphShellStates.jsx";
import { projectAuthorSemanticGraph } from "./authorSemanticProjection.js";
import { deriveInspectorDetail } from "./graphInspectorModel.js";
import { localizeEdgeType } from "./graphLocalize.js";
import { filterNodeIdsBySearchSubstring, firstMatchingNodeIdInOrder } from "./graphNodeSearch.js";
import { capGraphForUi } from "./graphUiLimits.js";
import { LS_GRAPH_STANDALONE_DETAIL_MIN_PX, readGraphDetailColumnPxStored } from "./graphDetailColumnWidth.js";
import {
  normalizeGraphEdgeId,
  normalizeGraphNodeId,
  resolveSelectedEdgeId,
  resolveSelectedNodeId,
} from "./graphViewState.js";
import WorkspaceGraphToolbar from "./WorkspaceGraphToolbar.jsx";
import { useGraphWorkspaceData } from "./hooks/useGraphWorkspaceData.js";

const LS_GRAPH_CANVAS_LAYOUT_MODE = "graphCanvasLayoutMode";
const LS_GRAPH_VIZ_MODE = "graphVizMode";
const LS_STANDALONE_DETAILS = "graphStandaloneDetailsVisible";
const LS_STANDALONE_LEGEND = "graphStandaloneLegendOpen";
const LS_EMBEDDED_LEGEND = "graphEmbeddedLegendOpen";

function readLsMode() {
  if (typeof window === "undefined") return "canvas";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_VIZ_MODE);
    return v === "cards" || v === "canvas" || v === "flow" ? v : "canvas";
  } catch {
    return "canvas";
  }
}

function readLsLayout() {
  if (typeof window === "undefined") return "force";
  try {
    return window.localStorage.getItem(LS_GRAPH_CANVAS_LAYOUT_MODE) === "circle" ? "circle" : "force";
  } catch {
    return "force";
  }
}

function readBoolLs(key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(key);
    if (v == null) return fallback;
    return v === "1";
  } catch {
    return fallback;
  }
}

export default function GraphWorkspacePanel({
  workId,
  workspaceId = "",
  selectedNodeId = "",
  onSelectNode,
  selectedEdgeId = "",
  onSelectEdge,
  mode = "embedded",
  title = "Graph",
  subtitle = null,
  traceContext = {},
  labMode = false,
  focusLayout = false,
  compactLayout = false,
  standaloneWorkGraphDepth = 1,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const standalone = mode === "standalone";
  const {
    wsId,
    graph,
    loading,
    error,
    wsGraphOpts,
    setWsGraphOpts,
    wsGraphStats,
    fetchNeighbors,
    expandNeighborsBusy,
    expandAggregatorNode,
  } =
    useGraphWorkspaceData(workspaceId, workId, { standaloneWorkGraphDepth });

  const [vizMode, setVizMode] = useState(() => (standalone ? "canvas" : readLsMode()));
  const [canvasLayoutMode, setCanvasLayoutMode] = useState(() => (standalone ? "force" : readLsLayout()));
  const [detailsVisible, setDetailsVisible] = useState(() => (standalone ? readBoolLs(LS_STANDALONE_DETAILS, !focusLayout) : true));
  const [legendOpen, setLegendOpen] = useState(() =>
    standalone ? readBoolLs(LS_STANDALONE_LEGEND, !focusLayout) : readBoolLs(LS_EMBEDDED_LEGEND, true),
  );
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(labMode);
  const [detailMinPx, setDetailMinPx] = useState(() => readGraphDetailColumnPxStored());
  const [localFindQuery, setLocalFindQuery] = useState("");
  const [centerCanvasNonce, setCenterCanvasNonce] = useState(0);
  const [centerCanvasNodeId, setCenterCanvasNodeId] = useState("");

  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_GRAPH_STANDALONE_DETAIL_MIN_PX, String(detailMinPx));
  }, [standalone, detailMinPx]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_DETAILS, detailsVisible ? "1" : "0");
  }, [standalone, detailsVisible]);
  useEffect(() => {
    if (standalone) window.localStorage.setItem(LS_STANDALONE_LEGEND, legendOpen ? "1" : "0");
    else window.localStorage.setItem(LS_EMBEDDED_LEGEND, legendOpen ? "1" : "0");
  }, [standalone, legendOpen]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_VIZ_MODE, vizMode);
  }, [standalone, vizMode]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_CANVAS_LAYOUT_MODE, canvasLayoutMode);
  }, [standalone, canvasLayoutMode]);

  const effectiveVizMode = standalone ? "canvas" : vizMode;
  const effectiveCanvasLayout = standalone ? "force" : canvasLayoutMode;
  const projectedGraph = useMemo(() => projectAuthorSemanticGraph(graph), [graph]);
  const resolvedSelectedEdgeId = useMemo(
    () => resolveSelectedEdgeId(projectedGraph, normalizeGraphEdgeId(selectedEdgeId)),
    [projectedGraph, selectedEdgeId],
  );
  const resolvedSelectedNodeId = useMemo(() => {
    if (resolvedSelectedEdgeId) return "";
    return resolveSelectedNodeId(projectedGraph, normalizeGraphNodeId(selectedNodeId));
  }, [projectedGraph, selectedNodeId, resolvedSelectedEdgeId]);
  const { displayGraph, capWarnings } = useMemo(
    () => capGraphForUi(projectedGraph, resolvedSelectedNodeId),
    [projectedGraph, resolvedSelectedNodeId],
  );
  const edgeTypeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const inspector = useMemo(
    () => deriveInspectorDetail(projectedGraph, resolvedSelectedNodeId, resolvedSelectedEdgeId, { edgeTypeLabel }),
    [projectedGraph, edgeTypeLabel, resolvedSelectedNodeId, resolvedSelectedEdgeId],
  );
  const nodeSearchMatchIds = useMemo(
    () => filterNodeIdsBySearchSubstring(displayGraph.nodes, localFindQuery),
    [displayGraph.nodes, localFindQuery],
  );
  const focusFirstLocalMatch = useCallback(() => {
    const first = firstMatchingNodeIdInOrder(displayGraph.nodes, nodeSearchMatchIds);
    if (!first) return;
    onSelectEdge?.("");
    onSelectNode?.(first);
    setCenterCanvasNodeId(first);
    setCenterCanvasNonce((n) => n + 1);
  }, [displayGraph.nodes, nodeSearchMatchIds, onSelectEdge, onSelectNode]);
  const traceSummary = describeTraceabilityState(traceContext);

  useEffect(() => {
    if (resolvedSelectedNodeId && resolvedSelectedNodeId !== normalizeGraphNodeId(selectedNodeId)) onSelectNode?.(resolvedSelectedNodeId);
  }, [resolvedSelectedNodeId, selectedNodeId, onSelectNode]);
  useEffect(() => {
    if (normalizeGraphEdgeId(selectedEdgeId) && !resolvedSelectedEdgeId) onSelectEdge?.("");
  }, [selectedEdgeId, resolvedSelectedEdgeId, onSelectEdge]);
  useEffect(() => {
    if (resolvedSelectedEdgeId && normalizeGraphNodeId(selectedNodeId)) onSelectNode?.("");
  }, [resolvedSelectedEdgeId, selectedNodeId, onSelectNode]);
  useEffect(() => {
    if (resolvedSelectedNodeId && normalizeGraphEdgeId(selectedEdgeId)) onSelectEdge?.("");
  }, [resolvedSelectedNodeId, selectedEdgeId, onSelectEdge]);

  const workIdTrim = String(workId || "").trim();
  const hasDataTarget = workIdTrim || String(workspaceId || "").trim();
  const isEmbedded = mode === "embedded";

  return (
    <Box sx={standalone ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" } : {}}>
      <Box sx={{ mb: standalone ? 1 : 2 }}>
        <Typography sx={{ fontWeight: 600, color: tk.text.primary }}>{title}</Typography>
        {subtitle ? <Box sx={{ mt: 0.5 }}>{subtitle}</Box> : null}
      </Box>
      {!hasDataTarget ? <GraphMissingWorkInline message={t("graph.workspacePanel.emptyHint")} /> : null}
      {loading ? <GraphLoadingInline /> : null}
      {error ? <GraphErrorAlert>{error}</GraphErrorAlert> : null}
      {!loading && !error && hasDataTarget ? (
        <>
          <WorkspaceGraphToolbar
            workspaceId={wsId}
            contextWorkId={workIdTrim}
            stats={wsGraphStats}
            value={wsGraphOpts}
            onChange={setWsGraphOpts}
            canvasMode={effectiveVizMode === "canvas"}
            localFindQuery={localFindQuery}
            onLocalFindChange={(e) => setLocalFindQuery(e.target.value)}
            onLocalFindClear={() => setLocalFindQuery("")}
            onFocusFirstMatch={focusFirstLocalMatch}
            localFindFocusDisabled={nodeSearchMatchIds.size === 0}
            detailsVisible={detailsVisible}
            legendOpen={legendOpen}
            diagnosticsOpen={diagnosticsOpen}
            onToggleDetails={() => setDetailsVisible((v) => !v)}
            onToggleLegend={() => setLegendOpen((v) => !v)}
            onToggleDiagnostics={() => setDiagnosticsOpen((v) => !v)}
            labMode={labMode}
          />
          {!standalone ? <GraphViewModeSwitch mode={vizMode} onChange={setVizMode} compact={compactLayout} /> : null}
          {projectedGraph.warnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Graph data was normalized</Alert> : null}
          {capWarnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Large graph - UI cap is active</Alert> : null}
          <Collapse in={legendOpen}>
            <GraphTypeLegend graph={displayGraph} />
          </Collapse>
          <Box
            sx={{
              flex: standalone ? 1 : undefined,
              minHeight: standalone ? 0 : { xs: "auto", md: isEmbedded ? 420 : 520 },
              display: "grid",
              gap: { xs: 2, md: standalone && detailsVisible ? 0 : 2 },
              gridTemplateColumns: !detailsVisible
                ? "minmax(0, 1fr)"
                : { xs: "minmax(0, 1fr)", md: standalone ? `minmax(0, 1fr) 6px ${detailMinPx}px` : "minmax(0, 1.7fr) minmax(280px, 1fr)" },
            }}
          >
            <Box sx={{ minWidth: 0, minHeight: standalone ? 0 : { xs: 280, md: isEmbedded ? 400 : 500 }, display: "flex", flexDirection: "column" }}>
              {effectiveVizMode === "cards" ? (
                <GraphVisualization graph={displayGraph} selectedNodeId={resolvedSelectedNodeId} onSelectNode={(id) => { onSelectEdge?.(""); onSelectNode?.(id); }} mode={mode} />
              ) : effectiveVizMode === "flow" ? (
                <GraphFlowView
                  graph={displayGraph}
                  selectedNodeId={resolvedSelectedNodeId}
                  selectedEdgeId={resolvedSelectedEdgeId}
                  onSelectNode={(id) => { onSelectEdge?.(""); onSelectNode?.(id); }}
                  onSelectEdge={(id) => { onSelectNode?.(""); onSelectEdge?.(id); }}
                />
              ) : (
                <GraphCanvasMvp
                  graph={displayGraph}
                  layoutMode={effectiveCanvasLayout}
                  onCanvasLayoutModeChange={standalone ? undefined : setCanvasLayoutMode}
                  selectedNodeId={resolvedSelectedNodeId}
                  selectedEdgeId={resolvedSelectedEdgeId}
                  onSelectNode={(id) => { onSelectEdge?.(""); onSelectNode?.(id); }}
                  onSelectEdge={(id) => { onSelectNode?.(""); onSelectEdge?.(id); }}
                  onAggregatorExpand={(_, expandEndpoint) => expandAggregatorNode(expandEndpoint)}
                  searchQuery={localFindQuery}
                  searchMatchIds={nodeSearchMatchIds}
                  centerRequestNonce={centerCanvasNonce}
                  centerRequestNodeId={centerCanvasNodeId}
                />
              )}
            </Box>
            <GraphSidePanel
              standalone={standalone}
              visible={detailsVisible}
              selectedNode={inspector.selectedNode}
              selectedEdge={inspector.selectedEdge}
              relatedEdges={inspector.relatedEdges}
              relatedEdgeRows={inspector.relatedEdgeRows}
              selectedEdgeReadable={inspector.selectedEdgeReadable}
              graphMeta={displayGraph.meta}
              onSelectNode={onSelectNode}
              onSelectEdge={onSelectEdge}
              onExpandWorkspaceNeighbors={wsId ? () => fetchNeighbors(resolvedSelectedNodeId) : undefined}
              onAggregatorExpand={(node, expandEndpoint) => {
                onSelectNode?.(node?.id || "");
                expandAggregatorNode(expandEndpoint);
              }}
              expandWorkspaceNeighborsBusy={expandNeighborsBusy}
              mode={mode}
              width={detailMinPx}
              onWidthChange={setDetailMinPx}
            />
          </Box>
          <Box sx={{ mt: 1, display: "flex", gap: 1 }}>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>nodes: {projectedGraph.nodeCount}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>edges: {projectedGraph.edgeCount}</Typography>
          </Box>
          {traceSummary.length > 0 ? <Alert severity="info" sx={{ mt: 1 }}>Opened from traceability context: {traceSummary.join(" · ")}</Alert> : null}
          {projectedGraph.nodeCount === 0 ? <Alert severity="info" sx={{ mt: 1 }}>This response has no nodes yet.</Alert> : null}
          <Box sx={{ mt: 1 }}>
            <GraphDebugInspector
              visible={labMode || diagnosticsOpen}
              maxHeight={standalone ? 200 : isEmbedded ? 180 : 240}
              payload={{
                work_id: projectedGraph.workId,
                meta: projectedGraph.meta,
                selected_node_id: resolvedSelectedNodeId,
                selected_edge_id: resolvedSelectedEdgeId,
                node_count: projectedGraph.nodeCount,
                edge_count: projectedGraph.edgeCount,
                warnings: projectedGraph.warnings,
                ui_cap_warnings: capWarnings,
              }}
            />
          </Box>
        </>
      ) : null}
    </Box>
  );
}
