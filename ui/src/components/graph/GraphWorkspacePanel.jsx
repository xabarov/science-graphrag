import React, { useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Slider from "@mui/material/Slider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { CursorSmallButton } from "../common/index.js";
import GraphVisualization from "./GraphVisualization.jsx";
import GraphCanvasMvp from "./GraphCanvasMvp.jsx";
import GraphFlowView from "./GraphFlowView.jsx";
import GraphDetailPanel from "./GraphDetailPanel.jsx";
import GraphTypeLegend from "./GraphTypeLegend.jsx";
import { GraphErrorAlert, GraphLoadingInline, GraphMissingWorkInline } from "./graphShellStates.jsx";
import { fetchWorkGraphNormalized } from "./graphAdapter.js";
import { capGraphForUi } from "./graphUiLimits.js";
import { deriveInspectorDetail } from "./graphInspectorModel.js";
import {
  normalizeGraphEdgeId,
  normalizeGraphNodeId,
  normalizeGraphPayload,
  resolveSelectedEdgeId,
  resolveSelectedNodeId,
} from "./graphViewState.js";
import { describeTraceabilityState } from "../work/traceabilityState.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import {
  clampGraphDetailColumnPx,
  GRAPH_DETAIL_COLUMN_PX_MAX,
  GRAPH_DETAIL_COLUMN_PX_MIN,
  GRAPH_DETAIL_COLUMN_PX_STEP,
  LS_GRAPH_STANDALONE_DETAIL_MIN_PX,
  readGraphDetailColumnPxStored,
} from "./graphDetailColumnWidth.js";

/**
 * @param {{
 *   workId: string,
 *   selectedNodeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   selectedEdgeId?: string,
 *   onSelectEdge?: (edgeId: string) => void,
 *   mode?: "embedded" | "standalone",
 *   title?: string,
 *   subtitle?: React.ReactNode,
 *   traceContext?: { chunkFingerprint?: string, section?: string, citation?: string, edgeId?: string },
 *   labMode?: boolean,
 *   compactLayout?: boolean,
 *   focusLayout?: boolean,
 * }} props
 */
const LS_STANDALONE_LEGEND = "graphStandaloneLegendOpen";
const LS_STANDALONE_TITLE = "graphStandaloneTitleOpen";
const LS_STANDALONE_ALERTS = "graphStandaloneAlertsOpen";
const LS_STANDALONE_DETAILS = "graphStandaloneDetailsVisible";
const LS_GRAPH_CANVAS_LAYOUT_MODE = "graphCanvasLayoutMode";
const LS_GRAPH_VIZ_MODE = "graphVizMode";

function readCanvasLayoutMode() {
  if (typeof window === "undefined") return "force";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_LAYOUT_MODE);
    if (v === "circle") return "circle";
    if (v === "force") return "force";
    return "force";
  } catch {
    return "force";
  }
}

function readVizMode() {
  if (typeof window === "undefined") return "canvas";
  try {
    const v = window.localStorage.getItem(LS_GRAPH_VIZ_MODE);
    if (v === "cards" || v === "canvas" || v === "flow") return v;
  } catch {
    /* ignore */
  }
  return "canvas";
}

function readBoolLs(key, fallback) {
  if (typeof window === "undefined") return fallback;
  try {
    const v = window.localStorage.getItem(key);
    if (v === null) return fallback;
    return v === "1";
  } catch {
    return fallback;
  }
}

export default function GraphWorkspacePanel({
  workId,
  selectedNodeId = "",
  onSelectNode,
  selectedEdgeId = "",
  onSelectEdge,
  mode = "embedded",
  compactLayout = false,
  focusLayout = false,
  title = "Graph",
  subtitle = null,
  traceContext = {},
  labMode = false,
}) {
  const [graph, setGraph] = useState(() => normalizeGraphPayload(null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [vizMode, setVizMode] = useState(
    /** @type {"cards" | "canvas" | "flow"} */ () => readVizMode(),
  );
  const [canvasLayoutMode, setCanvasLayoutMode] = useState(
    /** @type {"circle" | "force"} */ () => readCanvasLayoutMode(),
  );
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(labMode);

  const standaloneMax = mode === "standalone";
  const [detailMinPx, setDetailMinPx] = useState(() => readGraphDetailColumnPxStored());

  const [titleBlockOpen, setTitleBlockOpen] = useState(() => {
    if (!standaloneMax) return true;
    if (focusLayout) return false;
    return readBoolLs(LS_STANDALONE_TITLE, !compactLayout);
  });
  const [legendOpen, setLegendOpen] = useState(() => {
    if (!standaloneMax) return true;
    if (focusLayout) return false;
    return readBoolLs(LS_STANDALONE_LEGEND, !compactLayout);
  });
  const [alertsOpen, setAlertsOpen] = useState(() => {
    if (!standaloneMax) return true;
    if (focusLayout) return false;
    return readBoolLs(LS_STANDALONE_ALERTS, !compactLayout);
  });
  const [detailsVisible, setDetailsVisible] = useState(() => {
    if (!standaloneMax) return true;
    if (focusLayout) return false;
    return readBoolLs(LS_STANDALONE_DETAILS, true);
  });

  useEffect(() => {
    setDiagnosticsOpen(labMode);
  }, [labMode]);

  useEffect(() => {
    if (!standaloneMax) return;
    try {
      window.localStorage.setItem(LS_STANDALONE_TITLE, titleBlockOpen ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [standaloneMax, titleBlockOpen]);

  useEffect(() => {
    if (!standaloneMax) return;
    try {
      window.localStorage.setItem(LS_STANDALONE_LEGEND, legendOpen ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [standaloneMax, legendOpen]);

  useEffect(() => {
    if (!standaloneMax) return;
    try {
      window.localStorage.setItem(LS_STANDALONE_ALERTS, alertsOpen ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [standaloneMax, alertsOpen]);

  useEffect(() => {
    if (!standaloneMax) return;
    try {
      window.localStorage.setItem(LS_STANDALONE_DETAILS, detailsVisible ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [standaloneMax, detailsVisible]);

  useEffect(() => {
    if (!standaloneMax) return;
    try {
      window.localStorage.setItem(LS_GRAPH_STANDALONE_DETAIL_MIN_PX, String(detailMinPx));
    } catch {
      /* ignore */
    }
  }, [standaloneMax, detailMinPx]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_LAYOUT_MODE, canvasLayoutMode);
    } catch {
      /* ignore */
    }
  }, [canvasLayoutMode]);

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_VIZ_MODE, vizMode);
    } catch {
      /* ignore */
    }
  }, [vizMode]);

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
        setError(formatResearchApiError(err));
        setGraph(normalizeGraphPayload(null));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [workId]);

  const resolvedSelectedEdgeId = useMemo(
    () => resolveSelectedEdgeId(graph, normalizeGraphEdgeId(selectedEdgeId)),
    [graph, selectedEdgeId],
  );

  const resolvedSelectedNodeId = useMemo(() => {
    if (resolvedSelectedEdgeId) return "";
    return resolveSelectedNodeId(graph, normalizeGraphNodeId(selectedNodeId));
  }, [graph, selectedNodeId, resolvedSelectedEdgeId]);

  const { displayGraph, capWarnings } = useMemo(
    () => capGraphForUi(graph, resolvedSelectedNodeId),
    [graph, resolvedSelectedNodeId],
  );

  useEffect(() => {
    if (resolvedSelectedNodeId && resolvedSelectedNodeId !== normalizeGraphNodeId(selectedNodeId)) {
      onSelectNode?.(resolvedSelectedNodeId);
    }
  }, [onSelectNode, resolvedSelectedNodeId, selectedNodeId]);

  useEffect(() => {
    if (normalizeGraphEdgeId(selectedEdgeId) && !resolvedSelectedEdgeId) {
      onSelectEdge?.("");
    }
  }, [selectedEdgeId, resolvedSelectedEdgeId, onSelectEdge]);

  useEffect(() => {
    if (resolvedSelectedEdgeId && normalizeGraphNodeId(selectedNodeId)) {
      onSelectNode?.("");
    }
  }, [resolvedSelectedEdgeId, selectedNodeId, onSelectNode]);

  useEffect(() => {
    if (resolvedSelectedNodeId && normalizeGraphEdgeId(selectedEdgeId)) {
      onSelectEdge?.("");
    }
  }, [resolvedSelectedNodeId, selectedEdgeId, onSelectEdge]);

  const inspector = useMemo(
    () => deriveInspectorDetail(displayGraph, resolvedSelectedNodeId, resolvedSelectedEdgeId),
    [displayGraph, resolvedSelectedNodeId, resolvedSelectedEdgeId],
  );
  const isEmbedded = mode === "embedded";
  const traceSummary = describeTraceabilityState(traceContext);

  const mdDetailGridColumns = standaloneMax
    ? compactLayout
      ? `minmax(0, 1.7fr) 6px minmax(${detailMinPx}px, 1fr)`
      : `minmax(0, 2fr) 6px minmax(${detailMinPx}px, 1fr)`
    : `minmax(0, 1.7fr) minmax(280px, 1fr)`;

  const handleDetailSplitPointerDown = useCallback(
    (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      const el = e.currentTarget;
      const pointerId = e.pointerId;
      try {
        el.setPointerCapture(pointerId);
      } catch {
        /* ignore */
      }
      const startX = e.clientX;
      const startW = detailMinPx;
      const prevCursor = document.body.style.cursor;
      const prevUserSelect = document.body.style.userSelect;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      const onMove = (ev) => {
        const dx = ev.clientX - startX;
        setDetailMinPx(clampGraphDetailColumnPx(startW + dx));
      };
      const onEnd = () => {
        document.body.style.cursor = prevCursor;
        document.body.style.userSelect = prevUserSelect;
        try {
          el.releasePointerCapture(pointerId);
        } catch {
          /* ignore */
        }
        el.removeEventListener("pointermove", onMove);
        el.removeEventListener("pointerup", onEnd);
        el.removeEventListener("pointercancel", onEnd);
      };
      el.addEventListener("pointermove", onMove);
      el.addEventListener("pointerup", onEnd);
      el.addEventListener("pointercancel", onEnd);
    },
    [detailMinPx],
  );

  const rootSx = standaloneMax
    ? { flex: 1, minHeight: 0, display: "flex", flexDirection: "column", width: "100%" }
    : {};

  return (
    <Box sx={rootSx}>
      {standaloneMax ? (
        <Box sx={{ flexShrink: 0, mb: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.75, mb: 0.5 }}>
            <CursorSmallButton
              type="button"
              onClick={() => setTitleBlockOpen((o) => !o)}
              aria-expanded={titleBlockOpen}
              sx={{ minWidth: 32, px: 0.5 }}
            >
              <ExpandMoreIcon
                sx={{
                  fontSize: "1.1rem",
                  color: "rgba(255,255,255,0.65)",
                  transform: titleBlockOpen ? "rotate(0deg)" : "rotate(-90deg)",
                  transition: "transform 0.15s ease",
                }}
              />
            </CursorSmallButton>
            <Typography sx={{ fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>{title}</Typography>
          </Box>
          <Collapse in={titleBlockOpen}>
            {subtitle ? (
              typeof subtitle === "string" || typeof subtitle === "number" ? (
                <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.55)", mb: 1 }}>{subtitle}</Typography>
              ) : (
                <Box sx={{ mb: 1 }}>{subtitle}</Box>
              )
            ) : null}
          </Collapse>
        </Box>
      ) : (
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
      )}

      {!workId.trim() ? <GraphMissingWorkInline message="Pick a work to load graph context." /> : null}

      {loading ? <GraphLoadingInline /> : null}

      {error ? <GraphErrorAlert>{error}</GraphErrorAlert> : null}

      {!loading && !error && workId.trim() ? (
        <>
          {standaloneMax && (graph.warnings.length > 0 || capWarnings.length > 0) ? (
            <Box sx={{ flexShrink: 0, mb: 1 }}>
              <CursorSmallButton
                type="button"
                onClick={() => setAlertsOpen((o) => !o)}
                aria-expanded={alertsOpen}
                sx={{ mb: 0.5 }}
              >
                {alertsOpen ? "Hide" : "Show"} normalization / UI cap messages
              </CursorSmallButton>
              <Collapse in={alertsOpen}>
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
              </Collapse>
            </Box>
          ) : null}

          {!standaloneMax && graph.warnings.length > 0 ? (
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

          {!standaloneMax && capWarnings.length > 0 ? (
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

          <Box
            sx={
              standaloneMax
                ? { flex: 1, minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column" }
                : {}
            }
          >
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1.5, alignItems: "center", flexShrink: 0 }}>
            {standaloneMax ? (
              <>
                <CursorSmallButton
                  type="button"
                  onClick={() => setDetailsVisible((v) => !v)}
                  aria-pressed={detailsVisible}
                >
                  {detailsVisible ? "Hide" : "Show"} details panel
                </CursorSmallButton>
                <CursorSmallButton type="button" onClick={() => setLegendOpen((o) => !o)} aria-expanded={legendOpen}>
                  {legendOpen ? "Hide" : "Show"} type legend
                </CursorSmallButton>
                {detailsVisible ? (
                  <Box
                    sx={{
                      flex: "1 1 220px",
                      minWidth: 180,
                      maxWidth: 400,
                      px: 0.5,
                      alignSelf: "center",
                    }}
                  >
                    <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)", mb: 0.25 }}>
                      Detail column min width ({detailMinPx}px)
                    </Typography>
                    <Slider
                      size="small"
                      value={detailMinPx}
                      min={GRAPH_DETAIL_COLUMN_PX_MIN}
                      max={GRAPH_DETAIL_COLUMN_PX_MAX}
                      step={GRAPH_DETAIL_COLUMN_PX_STEP}
                      onChange={(_, v) => setDetailMinPx(clampGraphDetailColumnPx(v))}
                      sx={{
                        color: "rgba(129,140,248,0.85)",
                        py: 0.25,
                        "& .MuiSlider-thumb": { width: 12, height: 12 },
                        "& .MuiSlider-track": { border: "none" },
                      }}
                      aria-label="Detail column minimum width"
                    />
                  </Box>
                ) : null}
              </>
            ) : null}
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
            <CursorSmallButton
              type="button"
              onClick={() => setVizMode("flow")}
              sx={
                vizMode === "flow"
                  ? {
                      backgroundColor: "rgba(99, 102, 241, 0.15)",
                      borderColor: "rgba(99, 102, 241, 0.3)",
                      color: "rgba(129,140,248,0.92)",
                    }
                  : {}
              }
            >
              Flow
            </CursorSmallButton>
            {vizMode === "canvas" ? (
              <>
                <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.45)", mx: 0.25 }}>Canvas</Typography>
                <Tooltip
                  title="Static ring layout: pan and zoom only. Dragging a node switches to Force automatically."
                  placement="top"
                  enterDelay={400}
                >
                  <span>
                    <CursorSmallButton
                      type="button"
                      onClick={() => setCanvasLayoutMode("circle")}
                      sx={
                        canvasLayoutMode === "circle"
                          ? {
                              backgroundColor: "rgba(99, 102, 241, 0.15)",
                              borderColor: "rgba(99, 102, 241, 0.3)",
                              color: "rgba(129,140,248,0.92)",
                            }
                          : {}
                      }
                    >
                      Circle
                    </CursorSmallButton>
                  </span>
                </Tooltip>
                <Tooltip
                  title="Force-directed layout: drag nodes to rearrange; physics reheats after moves."
                  placement="top"
                  enterDelay={400}
                >
                  <span>
                    <CursorSmallButton
                      type="button"
                      onClick={() => setCanvasLayoutMode("force")}
                      sx={
                        canvasLayoutMode === "force"
                          ? {
                              backgroundColor: "rgba(99, 102, 241, 0.15)",
                              borderColor: "rgba(99, 102, 241, 0.3)",
                              color: "rgba(129,140,248,0.92)",
                            }
                          : {}
                      }
                    >
                      Force
                    </CursorSmallButton>
                  </span>
                </Tooltip>
              </>
            ) : null}
          </Box>

          {standaloneMax ? (
            <Collapse in={legendOpen}>
              <GraphTypeLegend graph={displayGraph} />
            </Collapse>
          ) : (
            <GraphTypeLegend graph={displayGraph} />
          )}

          <Box
            sx={{
              flex: standaloneMax ? 1 : undefined,
              display: "grid",
              gap: {
                xs: 2,
                md: standaloneMax && detailsVisible ? 0 : 2,
              },
              minHeight: standaloneMax ? 0 : { xs: "auto", md: isEmbedded ? 420 : 520 },
              gridTemplateColumns: !detailsVisible
                ? "minmax(0, 1fr)"
                : {
                    xs: "minmax(0, 1fr)",
                    md: mdDetailGridColumns,
                  },
              alignItems: "stretch",
            }}
          >
            <Box
              sx={{
                minWidth: 0,
                minHeight: standaloneMax ? 0 : { xs: 280, md: isEmbedded ? 400 : 500 },
                display: "flex",
                flexDirection: "column",
                alignSelf: "stretch",
                height: standaloneMax ? "100%" : "100%",
              }}
            >
              {vizMode === "cards" ? (
                <GraphVisualization
                  graph={displayGraph}
                  selectedNodeId={resolvedSelectedNodeId}
                  onSelectNode={(nodeId) => {
                    onSelectEdge?.("");
                    onSelectNode?.(nodeId);
                  }}
                  mode={mode}
                />
              ) : vizMode === "flow" ? (
                <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                  <GraphFlowView
                    graph={displayGraph}
                    selectedNodeId={resolvedSelectedNodeId}
                    selectedEdgeId={resolvedSelectedEdgeId}
                    onSelectNode={(nodeId) => {
                      onSelectEdge?.("");
                      onSelectNode?.(nodeId);
                    }}
                    onSelectEdge={(edgeId) => {
                      onSelectNode?.("");
                      onSelectEdge?.(edgeId);
                    }}
                  />
                </Box>
              ) : (
                <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                  <GraphCanvasMvp
                    graph={displayGraph}
                    layoutMode={canvasLayoutMode}
                    onCanvasLayoutModeChange={setCanvasLayoutMode}
                    selectedNodeId={resolvedSelectedNodeId}
                    selectedEdgeId={resolvedSelectedEdgeId}
                    onSelectNode={(nodeId) => {
                      onSelectEdge?.("");
                      onSelectNode?.(nodeId);
                    }}
                    onSelectEdge={(edgeId) => {
                      onSelectNode?.("");
                      onSelectEdge?.(edgeId);
                    }}
                  />
                </Box>
              )}
            </Box>
            {standaloneMax && detailsVisible ? (
              <Box
                onPointerDown={handleDetailSplitPointerDown}
                sx={{
                  display: { xs: "none", md: "block" },
                  width: 6,
                  flexShrink: 0,
                  cursor: "col-resize",
                  alignSelf: "stretch",
                  touchAction: "none",
                  borderRadius: "2px",
                  backgroundColor: "rgba(255,255,255,0.06)",
                  "&:hover": { backgroundColor: "rgba(255,255,255,0.12)" },
                }}
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize graph and detail panels"
              />
            ) : null}
            {detailsVisible ? (
              <Box sx={{ minWidth: 0, minHeight: standaloneMax ? 0 : { xs: 220, md: isEmbedded ? 400 : 500 }, display: "flex", flexDirection: "column" }}>
                <GraphDetailPanel
                  selectedNode={inspector.selectedNode}
                  selectedEdge={inspector.selectedEdge}
                  relatedEdges={inspector.relatedEdges}
                  relatedEdgeRows={inspector.relatedEdgeRows}
                  selectedEdgeReadable={inspector.selectedEdgeReadable}
                  graphMeta={displayGraph.meta}
                  onSelectNode={onSelectNode}
                  onSelectEdge={onSelectEdge}
                  mode={mode}
                />
              </Box>
            ) : null}
          </Box>
          </Box>

          <Box sx={{ mt: 2, display: "flex", flexWrap: "wrap", gap: 1, flexShrink: 0 }}>
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
                    maxHeight: isEmbedded ? 180 : 240,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {JSON.stringify(
                    {
                      work_id: graph.workId,
                      meta: graph.meta,
                      selected_node_id: resolvedSelectedNodeId,
                      selected_edge_id: resolvedSelectedEdgeId,
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
