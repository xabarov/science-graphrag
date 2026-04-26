import React, { useCallback, useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import BugReportOutlinedIcon from "@mui/icons-material/BugReportOutlined";
import ClearIcon from "@mui/icons-material/Clear";
import MyLocationOutlinedIcon from "@mui/icons-material/MyLocationOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import ViewSidebarOutlinedIcon from "@mui/icons-material/ViewSidebarOutlined";

import { CursorIconButton } from "../common/index.js";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { describeTraceabilityState } from "../work/traceabilityState.js";
import GraphCanvasMvp from "./GraphCanvasMvp.jsx";
import GraphDebugInspector from "./GraphDebugInspector.jsx";
import GraphFlowView from "./GraphFlowView.jsx";
import GraphSidePanel from "./GraphSidePanel.jsx";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import GraphViewModeSwitch from "./GraphViewModeSwitch.jsx";
import GraphVisualization from "./GraphVisualization.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "./graphShellStates.jsx";
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
  const [legendOpen, setLegendOpen] = useState(() => (standalone ? readBoolLs(LS_STANDALONE_LEGEND, !focusLayout) : true));
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
  }, [standalone, legendOpen]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_VIZ_MODE, vizMode);
  }, [standalone, vizMode]);
  useEffect(() => {
    if (!standalone) window.localStorage.setItem(LS_GRAPH_CANVAS_LAYOUT_MODE, canvasLayoutMode);
  }, [standalone, canvasLayoutMode]);

  const effectiveVizMode = standalone ? "canvas" : vizMode;
  const effectiveCanvasLayout = standalone ? "force" : canvasLayoutMode;
  const resolvedSelectedEdgeId = useMemo(() => resolveSelectedEdgeId(graph, normalizeGraphEdgeId(selectedEdgeId)), [graph, selectedEdgeId]);
  const resolvedSelectedNodeId = useMemo(() => {
    if (resolvedSelectedEdgeId) return "";
    return resolveSelectedNodeId(graph, normalizeGraphNodeId(selectedNodeId));
  }, [graph, selectedNodeId, resolvedSelectedEdgeId]);
  const { displayGraph, capWarnings } = useMemo(() => capGraphForUi(graph, resolvedSelectedNodeId), [graph, resolvedSelectedNodeId]);
  const edgeTypeLabel = useCallback((e) => localizeEdgeType(e, t), [t]);
  const inspector = useMemo(
    () => deriveInspectorDetail(displayGraph, resolvedSelectedNodeId, resolvedSelectedEdgeId, { edgeTypeLabel }),
    [displayGraph, edgeTypeLabel, resolvedSelectedNodeId, resolvedSelectedEdgeId],
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

  const hasDataTarget = workId.trim() || String(workspaceId || "").trim();
  const isEmbedded = mode === "embedded";

  return (
    <Box sx={standalone ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" } : {}}>
      <Box sx={{ mb: standalone ? 1 : 2 }}>
        <Typography sx={{ fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
        {subtitle ? <Box sx={{ mt: 0.5 }}>{subtitle}</Box> : null}
      </Box>
      {!hasDataTarget ? <GraphMissingWorkInline message={t("graph.workspacePanel.emptyHint")} /> : null}
      {loading ? <GraphLoadingInline /> : null}
      {error ? <GraphErrorAlert>{error}</GraphErrorAlert> : null}
      {!loading && !error && hasDataTarget ? (
        <>
          {wsId ? <WorkspaceGraphToolbar workspaceId={wsId} stats={wsGraphStats} value={wsGraphOpts} onChange={setWsGraphOpts} /> : null}
          {!standalone ? <GraphViewModeSwitch mode={vizMode} onChange={setVizMode} compact={compactLayout} /> : null}
          <Box sx={{ display: "flex", gap: 0.5, mb: 1, flexWrap: "wrap", alignItems: "center" }}>
            <Tooltip title={detailsVisible ? t("graph.workspacePanel.tooltipDetailsHide") : t("graph.workspacePanel.tooltipDetailsShow")}>
              <CursorIconButton
                type="button"
                aria-label={t("graph.workspacePanel.ariaToggleDetails")}
                onClick={() => setDetailsVisible((v) => !v)}
                sx={{
                  ...(detailsVisible
                    ? { borderColor: "rgba(99,102,241,0.35)", color: "rgba(129,140,248,0.95)" }
                    : { opacity: 0.75 }),
                }}
              >
                <ViewSidebarOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconButton>
            </Tooltip>
            {standalone ? (
              <Tooltip title={legendOpen ? t("graph.workspacePanel.tooltipLegendHide") : t("graph.workspacePanel.tooltipLegendShow")}>
                <CursorIconButton
                  type="button"
                  aria-label={t("graph.workspacePanel.ariaToggleLegend")}
                  onClick={() => setLegendOpen((v) => !v)}
                  sx={{
                    ...(legendOpen
                      ? { borderColor: "rgba(99,102,241,0.35)", color: "rgba(129,140,248,0.95)" }
                      : { opacity: 0.75 }),
                  }}
                >
                  <LayersOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </Tooltip>
            ) : null}
            {!labMode ? (
              <Tooltip
                title={
                  diagnosticsOpen
                    ? t("graph.workspacePanel.tooltipDiagnosticsHide")
                    : t("graph.workspacePanel.tooltipDiagnosticsShow")
                }
              >
                <CursorIconButton
                  type="button"
                  aria-label={t("graph.workspacePanel.ariaToggleDiagnostics")}
                  onClick={() => setDiagnosticsOpen((v) => !v)}
                  sx={{
                    ...(diagnosticsOpen
                      ? { borderColor: "rgba(99,102,241,0.35)", color: "rgba(129,140,248,0.95)" }
                      : { opacity: 0.75 }),
                  }}
                >
                  <BugReportOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </Tooltip>
            ) : null}
          </Box>
          {graph.warnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Graph data was normalized</Alert> : null}
          {capWarnings.length > 0 ? <Alert severity="info" sx={{ mb: 1 }}>Large graph - UI cap is active</Alert> : null}
          {standalone ? (
            <Collapse in={legendOpen}>
              <GraphTypeLegend graph={displayGraph} />
            </Collapse>
          ) : (
            <GraphTypeLegend graph={displayGraph} />
          )}
          {effectiveVizMode === "canvas" ? (
            <Box sx={{ mb: 1, display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
              <TextField
                size="small"
                variant="outlined"
                value={localFindQuery}
                onChange={(e) => setLocalFindQuery(e.target.value)}
                placeholder={t("graph.localFind.placeholder")}
                inputProps={{ "aria-label": t("graph.localFind.aria") }}
                sx={{
                  minWidth: 200,
                  flex: "1 1 220px",
                  maxWidth: 480,
                  "& .MuiOutlinedInput-root": {
                    fontSize: "0.8125rem",
                    backgroundColor: "rgba(255,255,255,0.04)",
                    color: "rgba(255,255,255,0.9)",
                  },
                  "& .MuiOutlinedInput-notchedOutline": { borderColor: "rgba(255,255,255,0.12)" },
                  "& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline": {
                    borderColor: "rgba(255,255,255,0.18)",
                  },
                  "& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
                    borderColor: "rgba(99, 102, 241, 0.5)",
                    borderWidth: "1px",
                  },
                }}
                InputProps={{
                  endAdornment: localFindQuery ? (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        aria-label={t("graph.localFind.clearAria")}
                        onClick={() => setLocalFindQuery("")}
                        edge="end"
                        sx={{ color: "rgba(255,255,255,0.5)" }}
                      >
                        <ClearIcon fontSize="small" />
                      </IconButton>
                    </InputAdornment>
                  ) : null,
                }}
              />
              <Tooltip title={t("graph.localFind.focusFirstTooltip")}>
                <span>
                  <CursorIconButton
                    type="button"
                    aria-label={t("graph.localFind.focusFirst")}
                    onClick={focusFirstLocalMatch}
                    disabled={nodeSearchMatchIds.size === 0}
                  >
                    <MyLocationOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                  </CursorIconButton>
                </span>
              </Tooltip>
            </Box>
          ) : null}
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
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>nodes: {graph.nodeCount}</Typography>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)" }}>edges: {graph.edgeCount}</Typography>
          </Box>
          {traceSummary.length > 0 ? <Alert severity="info" sx={{ mt: 1 }}>Opened from traceability context: {traceSummary.join(" · ")}</Alert> : null}
          {graph.nodeCount === 0 ? <Alert severity="info" sx={{ mt: 1 }}>This response has no nodes yet.</Alert> : null}
          <Box sx={{ mt: 1 }}>
            <GraphDebugInspector
              visible={labMode || diagnosticsOpen}
              maxHeight={standalone ? 200 : isEmbedded ? 180 : 240}
              payload={{
                work_id: graph.workId,
                meta: graph.meta,
                selected_node_id: resolvedSelectedNodeId,
                selected_edge_id: resolvedSelectedEdgeId,
                node_count: graph.nodeCount,
                edge_count: graph.edgeCount,
                warnings: graph.warnings,
                ui_cap_warnings: capWarnings,
              }}
            />
          </Box>
        </>
      ) : null}
    </Box>
  );
}
