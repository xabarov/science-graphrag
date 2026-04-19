import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import Box from "@mui/material/Box";
import Slider from "@mui/material/Slider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import CenterFocusStrongOutlinedIcon from "@mui/icons-material/CenterFocusStrongOutlined";
import FitScreenOutlinedIcon from "@mui/icons-material/FitScreenOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LinkOffOutlinedIcon from "@mui/icons-material/LinkOffOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import ZoomOutMapOutlinedIcon from "@mui/icons-material/ZoomOutMapOutlined";

import { CursorIconButton } from "../common/index.js";
import {
  computeFitTransform,
  computeWorldLayout,
  screenToWorld,
  worldRadiusForNodeCount,
  worldToScreen,
} from "./graphCanvasTransform.js";
import {
  edgeTypeCanvasLabel,
  getScienceGraphNodeStyle,
  truncateCanvasLabel,
} from "./graphCanvasStyle.js";
import { clipSegmentByDiscInsets, distancePointToSegment } from "./graphCanvasGeometry.js";
import { getGraphLayoutSignature } from "./graphFlowAdapter.js";
import { buildSimulationState } from "./graphSimulationAdapter.js";
import { useScienceGraphForceSimulation } from "./physics/useScienceGraphForceSimulation.js";
import { percentToRepulsion, REPULSION_DEFAULT_PERCENT } from "./physics/simConstants.js";

const LABEL_FONT =
  '600 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';
const EDGE_LABEL_FONT =
  '400 10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';

const NODE_RADIUS = 12;
const ARROW_HEAD_LEN = 7;
const ARROW_HEAD_HW = 4;
const EDGE_HOVER_THRESHOLD_PX = 8;
const MIN_SCALE = 0.06;
const MAX_SCALE = 8;
const DRAG_THRESHOLD_PX = 5;
const FIT_PADDING = 40;
/** World-units jitter on force restart (osint-style re-spread around circle seed). */
const FORCE_RESTART_JITTER_WORLD = 56;
/** Minimum drawing height before container measurement (matches workspace column expectations). */
const MIN_CANVAS_HEIGHT = 280;
/** Prevent fit-to-view from shrinking so far that nodes look like an empty canvas. */
const MIN_FIT_SCALE = 0.11;

const LS_GRAPH_CANVAS_REPULSION = "graphCanvasRepulsionPercent";

/**
 * @param {{ scale: number, tx: number, ty: number }} fit
 */
function clampFitTransform(fit) {
  const scale = Math.max(fit.scale, MIN_FIT_SCALE);
  return { ...fit, scale };
}

function readRepulsionPercentStored() {
  if (typeof window === "undefined") return REPULSION_DEFAULT_PERCENT;
  try {
    const v = window.localStorage.getItem(LS_GRAPH_CANVAS_REPULSION);
    if (v == null) return REPULSION_DEFAULT_PERCENT;
    const n = Number(v);
    if (!Number.isFinite(n)) return REPULSION_DEFAULT_PERCENT;
    return Math.min(100, Math.max(0, n));
  } catch {
    return REPULSION_DEFAULT_PERCENT;
  }
}

/**
 * Phase 4.2–4.3: canvas with world coords, zoom/pan, fit/reset/center, keyboard (Escape). Wave 4.2: draw order — edge strokes, node discs, edge labels (active last), node labels (active last).
 * @param {{
 *   graph: { nodes: Array<{ id: string }>, edges: Array<{ source: string, target: string, id?: string }> },
 *   selectedNodeId: string,
 *   selectedEdgeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 *   layoutMode?: "circle" | "force",
 *   onCanvasLayoutModeChange?: (mode: "circle" | "force") => void,
 * }} props
 */
export default function GraphCanvasMvp({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
  layoutMode = "circle",
  onCanvasLayoutModeChange,
}) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const canvasHostRef = useRef(null);
  const positionsRef = useRef(new Map());
  const transformRef = useRef({ scale: 1, tx: 0, ty: 0 });
  const [transform, setTransform] = useState({ scale: 1, tx: 0, ty: 0 });
  const [hostSize, setHostSize] = useState({ width: 0, height: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [hoveredEdgeId, setHoveredEdgeId] = useState("");
  const [canvasCursor, setCanvasCursor] = useState("grab");
  const hoverPickPendingRef = useRef(false);
  const hoverClientRef = useRef({ x: 0, y: 0 });
  const dragRef = useRef({
    active: false,
    moved: false,
    startX: 0,
    startY: 0,
    startTx: 0,
    startTy: 0,
    pointerId: null,
  });
  const nodeDragRef = useRef({
    active: false,
    moved: false,
    nodeId: "",
    startX: 0,
    startY: 0,
    pointerId: null,
  });
  const draggedNodePositionRef = useRef(null);
  const fixedNodesRef = useRef(new Set());
  const prevLayoutModeRef = useRef(layoutMode);
  const simNodesRef = useRef([]);

  const [simNodes, setSimNodes] = useState([]);
  const [simLinks, setSimLinks] = useState([]);
  const [isSimulationStable, setIsSimulationStable] = useState(false);
  const [repulsionPercent, setRepulsionPercent] = useState(() => readRepulsionPercentStored());
  const [forceSimRunNonce, setForceSimRunNonce] = useState(0);
  const [physicsReheatNonce, setPhysicsReheatNonce] = useState(0);
  const [pinnedNodeCount, setPinnedNodeCount] = useState(0);

  const layoutKey = useMemo(() => graph.nodes.map((n) => n.id).join("\0"), [graph.nodes]);
  const topologySignature = useMemo(
    () => getGraphLayoutSignature({ nodes: graph.nodes, edges: graph.edges }),
    [graph.nodes, graph.edges],
  );
  const simulationSignature = useMemo(
    () => `${topologySignature}|${forceSimRunNonce}|${physicsReheatNonce}`,
    [topologySignature, forceSimRunNonce, physicsReheatNonce],
  );

  const bumpPhysicsReheat = useCallback(() => {
    setPhysicsReheatNonce((n) => n + 1);
  }, []);
  const layoutWorldRadius = useMemo(() => worldRadiusForNodeCount(graph.nodes.length), [graph.nodes.length]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);

  const repulsionStrength = useMemo(() => percentToRepulsion(repulsionPercent), [repulsionPercent]);

  const canvasSize = useMemo(
    () => ({
      width: Math.max(1, hostSize.width || 1),
      height: Math.max(MIN_CANVAS_HEIGHT, hostSize.height || MIN_CANVAS_HEIGHT),
    }),
    [hostSize.height, hostSize.width],
  );

  simNodesRef.current = simNodes;

  const getViewportDims = useCallback(() => {
    const host = canvasHostRef.current;
    const w = Math.max(1, hostSize.width || host?.clientWidth || 1);
    const h = Math.max(MIN_CANVAS_HEIGHT, hostSize.height || host?.clientHeight || MIN_CANVAS_HEIGHT);
    return { w, h };
  }, [hostSize.height, hostSize.width]);

  /** @param {"circle" | "force" | "auto"} mode */
  const applyFitInner = useCallback(
    (mode = "auto") => {
      if (graph.nodes.length === 0) return;
      const { w, h } = getViewportDims();
      const useForce =
        (mode === "force" || (mode === "auto" && layoutMode === "force")) && simNodesRef.current.length > 0;
      const positions = useForce
        ? new Map(simNodesRef.current.map((n) => [n.id, { x: n.x, y: n.y }]))
        : computeWorldLayout(graph.nodes, layoutWorldRadius);
      positionsRef.current = positions;
      const next = clampFitTransform(computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING));
      const prev = transformRef.current;
      if (prev.scale === next.scale && prev.tx === next.tx && prev.ty === next.ty) {
        return;
      }
      transformRef.current = next;
      setTransform(next);
    },
    // graph / graph.nodes intentionally omitted: parent often passes a new array identity each render,
    // which would recreate this callback every frame and retrigger fit effects → tight loop + high CPU.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- stable via topologySignature
    [getViewportDims, topologySignature, layoutWorldRadius, layoutMode],
  );

  const applyFit = useCallback(() => {
    applyFitInner("auto");
  }, [applyFitInner]);

  const zoomAtViewportCenter = useCallback(
    (factor) => {
      const { w, h } = getViewportDims();
      const cx = w / 2;
      const cy = h / 2;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(cx, cy, scale, tx, ty);
      const newScale = Math.min(Math.max(scale * factor, MIN_SCALE), MAX_SCALE);
      const next = {
        scale: newScale,
        tx: cx - world.x * newScale,
        ty: cy - world.y * newScale,
      };
      transformRef.current = next;
      setTransform(next);
    },
    [getViewportDims],
  );

  const forceSimEnabled = layoutMode === "force" && simNodes.length > 0;

  useScienceGraphForceSimulation(
    forceSimEnabled,
    simNodes,
    setSimNodes,
    simLinks,
    repulsionStrength,
    isSimulationStable,
    setIsSimulationStable,
    fixedNodesRef,
    draggedNodePositionRef,
    canvasSize,
    simulationSignature,
  );

  useEffect(() => {
    try {
      window.localStorage.setItem(LS_GRAPH_CANVAS_REPULSION, String(repulsionPercent));
    } catch {
      /* ignore */
    }
  }, [repulsionPercent]);

  useLayoutEffect(() => {
    const built = buildSimulationState(graph);
    setSimNodes(built.nodes);
    setSimLinks(built.links);
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
    setForceSimRunNonce(0);
    setPhysicsReheatNonce(0);
    const positions = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    positionsRef.current = positions;
    if (layoutMode === "force" && built.nodes.length > 0) {
      const { w, h } = getViewportDims();
      const next = clampFitTransform(computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING));
      transformRef.current = next;
      setTransform(next);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- topology-only reseed; layoutMode read for conditional fit without re-running on mode toggle
  }, [topologySignature, getViewportDims]);

  useLayoutEffect(() => {
    if (layoutMode !== "force" || graph.nodes.length === 0) return;
    if (simNodes.length === 0) return;
    applyFitInner("force");
    // graph.nodes.length omitted: same as topologySignature + simNodes.length for emptiness
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layoutMode, simNodes.length, topologySignature, applyFitInner]);

  const handleRestartForceSimulation = useCallback(() => {
    if (layoutMode !== "force" || graph.nodes.length === 0) return;
    fixedNodesRef.current.clear();
    draggedNodePositionRef.current = null;
    setPinnedNodeCount(0);
    const built = buildSimulationState(graph, { jitterWorld: FORCE_RESTART_JITTER_WORLD });
    setSimLinks(built.links);
    setSimNodes(built.nodes);
    setForceSimRunNonce((n) => n + 1);
    setPhysicsReheatNonce(0);
    setIsSimulationStable(false);
    const positions = new Map(built.nodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    positionsRef.current = positions;
    const { w, h } = getViewportDims();
    const next = clampFitTransform(computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING));
    transformRef.current = next;
    setTransform(next);
    // graph omitted: use topologySignature so restart handler is stable across graph object identity churn
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getViewportDims, topologySignature, layoutMode]);

  const handleUnpinAll = useCallback(() => {
    if (layoutMode !== "force") return;
    if (fixedNodesRef.current.size === 0) return;
    fixedNodesRef.current.clear();
    setPinnedNodeCount(0);
    setIsSimulationStable(false);
  }, [layoutMode]);

  useEffect(() => {
    const prev = prevLayoutModeRef.current;
    prevLayoutModeRef.current = layoutMode;
    if (prev === "force" && layoutMode === "circle") {
      const raf = requestAnimationFrame(() => {
        applyFitInner("circle");
      });
      return () => cancelAnimationFrame(raf);
    }
    return undefined;
  }, [layoutMode, applyFitInner]);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  useEffect(() => {
    if (layoutMode === "force") return;
    let raf = 0;
    raf = requestAnimationFrame(() => {
      applyFitInner("circle");
    });
    return () => cancelAnimationFrame(raf);
  }, [layoutKey, layoutMode, applyFitInner]);

  useEffect(() => {
    let raf = 0;
    raf = requestAnimationFrame(() => {
      setHoveredNodeId("");
      setHoveredEdgeId("");
      setCanvasCursor("grab");
    });
    return () => cancelAnimationFrame(raf);
  }, [layoutKey]);

  useEffect(() => {
    const el = canvasHostRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (!cr) return;
      const nw = Math.max(1, Math.floor(cr.width));
      const nh = Math.max(MIN_CANVAS_HEIGHT, Math.floor(cr.height));
      setHostSize((prev) => (prev.width === nw && prev.height === nh ? prev : { width: nw, height: nh }));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const getPositionsForFrame = useCallback(() => {
    const dragging = nodeDragRef.current.active;
    if (simNodes.length > 0 && (layoutMode === "force" || dragging)) {
      return new Map(simNodes.map((n) => [n.id, { x: n.x, y: n.y }]));
    }
    return computeWorldLayout(graph.nodes, layoutWorldRadius);
  }, [layoutMode, simNodes, graph.nodes, layoutWorldRadius]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const host = canvasHostRef.current;
    if (!canvas || !host) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const { w, h } = getViewportDims();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a0a0a";
    ctx.fillRect(0, 0, w, h);

    const { scale, tx, ty } = transformRef.current;
    const positions = getPositionsForFrame();
    positionsRef.current = positions;

    for (const edge of graph.edges) {
      const p0w = positions.get(edge.source);
      const p1w = positions.get(edge.target);
      if (!p0w || !p1w) continue;
      const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
      const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
      const edgeActive = edge.id === hoveredEdgeId || edge.id === selectedEdgeId;
      const clipped = clipSegmentByDiscInsets(p0, p1, NODE_RADIUS, NODE_RADIUS);
      ctx.strokeStyle = edgeActive ? "rgba(255,255,255,0.38)" : "rgba(255,255,255,0.12)";
      ctx.lineWidth = edgeActive ? 1.75 : 1;
      if (clipped) {
        const { ax, ay, bx, by, ux, uy } = clipped;
        const lineEndX = bx - ux * ARROW_HEAD_LEN;
        const lineEndY = by - uy * ARROW_HEAD_LEN;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(lineEndX, lineEndY);
        ctx.stroke();
        const px = -uy;
        const py = ux;
        ctx.beginPath();
        ctx.moveTo(bx, by);
        ctx.lineTo(lineEndX + px * ARROW_HEAD_HW, lineEndY + py * ARROW_HEAD_HW);
        ctx.lineTo(lineEndX - px * ARROW_HEAD_HW, lineEndY - py * ARROW_HEAD_HW);
        ctx.closePath();
        ctx.fillStyle = edgeActive ? "rgba(255,255,255,0.38)" : "rgba(255,255,255,0.2)";
        ctx.fill();
      } else {
        ctx.beginPath();
        ctx.moveTo(p0.x, p0.y);
        ctx.lineTo(p1.x, p1.y);
        ctx.stroke();
      }
    }

    const nodesForDiscs = [...graph.nodes].sort((a, b) => {
      const rank = (n) => (n.id === hoveredNodeId || n.id === selectedNodeId ? 1 : 0);
      const dr = rank(a) - rank(b);
      if (dr !== 0) return dr;
      return String(a.id).localeCompare(String(b.id));
    });
    for (const node of nodesForDiscs) {
      const pw = positions.get(node.id);
      if (!pw) continue;
      const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
      const sel = node.id === selectedNodeId;
      const r = NODE_RADIUS;
      const style = getScienceGraphNodeStyle(node.type, {
        selected: sel,
        hovered: !sel && node.id === hoveredNodeId,
      });
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = style.fill;
      ctx.fill();
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = style.lineWidth;
      ctx.stroke();
    }

    ctx.font = EDGE_LABEL_FONT;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const edgesForLabels = [...graph.edges].sort((a, b) => {
      const rank = (e) => (e.id === hoveredEdgeId || e.id === selectedEdgeId ? 1 : 0);
      const dr = rank(a) - rank(b);
      if (dr !== 0) return dr;
      return String(a.id ?? "").localeCompare(String(b.id ?? ""));
    });
    for (const edge of edgesForLabels) {
      const p0w = positions.get(edge.source);
      const p1w = positions.get(edge.target);
      if (!p0w || !p1w) continue;
      const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
      const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
      const elabel = edgeTypeCanvasLabel(edge.type);
      if (!elabel || elabel === "—") continue;
      const midX = (p0.x + p1.x) / 2;
      const midY = (p0.y + p1.y) / 2;
      const metrics = ctx.measureText(elabel);
      const padX = 4;
      const bw = metrics.width + padX * 2;
      const bh = 16;
      const eHover = edge.id === hoveredEdgeId || edge.id === selectedEdgeId;
      ctx.fillStyle = eHover ? "rgba(40, 40, 40, 0.96)" : "rgba(26, 26, 26, 0.94)";
      ctx.fillRect(midX - bw / 2, midY - bh / 2, bw, bh);
      ctx.strokeStyle = eHover ? "rgba(255, 255, 255, 0.2)" : "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
      ctx.strokeRect(midX - bw / 2, midY - bh / 2, bw, bh);
      ctx.fillStyle = eHover ? "rgba(255, 255, 255, 0.82)" : "rgba(255, 255, 255, 0.62)";
      ctx.fillText(elabel, midX, midY);
    }

    ctx.font = LABEL_FONT;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const nodesForLabels = [...graph.nodes].sort((a, b) => {
      const rank = (n) => (n.id === hoveredNodeId || n.id === selectedNodeId ? 1 : 0);
      const dr = rank(a) - rank(b);
      if (dr !== 0) return dr;
      return String(a.id).localeCompare(String(b.id));
    });
    for (const node of nodesForLabels) {
      const pw = positions.get(node.id);
      if (!pw) continue;
      const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
      const sel = node.id === selectedNodeId;
      const rawLabel =
        node.displayLabel != null && String(node.displayLabel).trim()
          ? node.displayLabel
          : node.label != null && String(node.label).trim()
            ? node.label
            : node.id;
      const text = truncateCanvasLabel(rawLabel);
      const metrics = ctx.measureText(text);
      const padX = 6;
      const boxW = metrics.width + padX * 2;
      const boxH = 20;
      const boxTop = p.y + NODE_RADIUS + 4;
      const midY = boxTop + boxH / 2;
      ctx.fillStyle = "rgba(26, 26, 26, 0.95)";
      ctx.fillRect(p.x - boxW / 2, boxTop, boxW, boxH);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1;
      ctx.strokeRect(p.x - boxW / 2, boxTop, boxW, boxH);
      ctx.fillStyle = sel ? "rgba(255, 255, 255, 0.92)" : "rgba(255, 255, 255, 0.82)";
      ctx.fillText(text, p.x, midY);
    }
  }, [
    getPositionsForFrame,
    getViewportDims,
    graph.edges,
    graph.nodes,
    hoveredEdgeId,
    hoveredNodeId,
    selectedEdgeId,
    selectedNodeId,
  ]);

  useEffect(() => {
    draw();
  }, [draw, transform]);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const onWheel = (e) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(mx, my, scale, tx, ty);
      const factor = e.deltaY > 0 ? 0.92 : 1.08;
      const newScale = Math.min(Math.max(scale * factor, MIN_SCALE), MAX_SCALE);
      const newTx = mx - world.x * newScale;
      const newTy = my - world.y * newScale;
      const next = { scale: newScale, tx: newTx, ty: newTy };
      transformRef.current = next;
      setTransform(next);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function hitTestWorld(wx, wy, posMap = positionsRef.current) {
    for (const node of nodeById.values()) {
      const p = posMap.get(node.id);
      if (!p) continue;
      const dx = wx - p.x;
      const dy = wy - p.y;
      if (dx * dx + dy * dy <= NODE_RADIUS * NODE_RADIUS) {
        return node.id;
      }
    }
    return null;
  }

  function hitTestClosestEdgeId(screenX, screenY, positions, scale, tx, ty) {
    let best = "";
    let bestD = EDGE_HOVER_THRESHOLD_PX + 1;
    for (const edge of graph.edges) {
      const p0w = positions.get(edge.source);
      const p1w = positions.get(edge.target);
      if (!p0w || !p1w) continue;
      const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
      const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
      const d = distancePointToSegment(screenX, screenY, p0.x, p0.y, p1.x, p1.y);
      if (d < bestD) {
        bestD = d;
        best = edge.id;
      }
    }
    return bestD <= EDGE_HOVER_THRESHOLD_PX ? best : "";
  }

  function queueHoverPick(clientX, clientY) {
    hoverClientRef.current = { x: clientX, y: clientY };
    if (hoverPickPendingRef.current) return;
    hoverPickPendingRef.current = true;
    requestAnimationFrame(() => {
      hoverPickPendingRef.current = false;
      const { x: cx, y: cy } = hoverClientRef.current;
      const canvas = canvasRef.current;
      if (!canvas) return;
      if (dragRef.current.active && dragRef.current.moved) return;
      if (nodeDragRef.current.active && nodeDragRef.current.moved) return;
      const rect = canvas.getBoundingClientRect();
      const lx = cx - rect.left;
      const ly = cy - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(lx, ly, scale, tx, ty);
      const posMap = getPositionsForFrame();
      const nodeId = hitTestWorld(world.x, world.y, posMap) ?? "";
      if (nodeId) {
        setHoveredNodeId((prev) => (prev === nodeId ? prev : nodeId));
        setHoveredEdgeId("");
        setCanvasCursor("pointer");
        return;
      }
      setHoveredNodeId("");
      const edgeId = hitTestClosestEdgeId(lx, ly, posMap, scale, tx, ty);
      setHoveredEdgeId((prev) => (prev === edgeId ? prev : edgeId));
      setCanvasCursor(edgeId ? "pointer" : "grab");
    });
  }

  function handlePointerDown(ev) {
    if (ev.button !== 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const { scale, tx, ty } = transformRef.current;

    if (simNodes.length > 0) {
      const world = screenToWorld(x, y, scale, tx, ty);
      const posMap = getPositionsForFrame();
      const nodeId = hitTestWorld(world.x, world.y, posMap);
      if (nodeId) {
        if (layoutMode === "circle" && onCanvasLayoutModeChange) {
          flushSync(() => onCanvasLayoutModeChange("force"));
        }
        canvas.setPointerCapture(ev.pointerId);
        nodeDragRef.current = {
          active: true,
          moved: false,
          nodeId,
          startX: x,
          startY: y,
          pointerId: ev.pointerId,
        };
        draggedNodePositionRef.current = { id: nodeId, x: world.x, y: world.y };
        setSimNodes((prev) =>
          prev.map((n) => (n.id === nodeId ? { ...n, x: world.x, y: world.y, vx: 0, vy: 0 } : n)),
        );
        return;
      }
    }

    canvas.setPointerCapture(ev.pointerId);
    dragRef.current = {
      active: true,
      moved: false,
      startX: x,
      startY: y,
      startTx: tx,
      startTy: ty,
      pointerId: ev.pointerId,
    };
  }

  function handleCanvasPointerMove(ev) {
    const nd = nodeDragRef.current;
    if (nd.active) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const dx = x - nd.startX;
      const dy = y - nd.startY;
      if (!nd.moved && dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
        nd.moved = true;
        setHoveredNodeId("");
        setHoveredEdgeId("");
        setCanvasCursor("grabbing");
        setIsSimulationStable(false);
        bumpPhysicsReheat();
      }
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(x, y, scale, tx, ty);
      draggedNodePositionRef.current = { id: nd.nodeId, x: world.x, y: world.y };
      setSimNodes((prev) =>
        prev.map((n) => (n.id === nd.nodeId ? { ...n, x: world.x, y: world.y, vx: 0, vy: 0 } : n)),
      );
      return;
    }

    const d = dragRef.current;
    if (d.active) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const dx = x - d.startX;
      const dy = y - d.startY;
      if (!d.moved && dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
        d.moved = true;
        setHoveredNodeId("");
        setHoveredEdgeId("");
        setCanvasCursor("grabbing");
      }
      if (d.moved) {
        const next = { scale: transformRef.current.scale, tx: d.startTx + dx, ty: d.startTy + dy };
        transformRef.current = next;
        setTransform(next);
      }
      return;
    }
    queueHoverPick(ev.clientX, ev.clientY);
  }

  function handleCanvasPointerLeave() {
    setHoveredNodeId("");
    setHoveredEdgeId("");
    setCanvasCursor("grab");
  }

  function handlePointerUp(ev) {
    const canvas = canvasRef.current;
    const nd = nodeDragRef.current;
    if (nd.active) {
      try {
        canvas?.releasePointerCapture(ev.pointerId);
      } catch {
        /* ignore */
      }
      const { nodeId, moved } = nd;
      const pinAfterDrop = moved && isSimulationStable;
      nodeDragRef.current = {
        active: false,
        moved: false,
        nodeId: "",
        startX: 0,
        startY: 0,
        pointerId: null,
      };
      draggedNodePositionRef.current = null;
      if (moved) {
        setIsSimulationStable(false);
        bumpPhysicsReheat();
      }
      if (pinAfterDrop) {
        fixedNodesRef.current.add(nodeId);
        setPinnedNodeCount(fixedNodesRef.current.size);
      }
      if (!moved) {
        onSelectEdge?.("");
        onSelectNode?.(nodeId);
      }
      queueHoverPick(ev.clientX, ev.clientY);
      return;
    }

    const d = dragRef.current;
    if (!d.active) return;
    try {
      canvas?.releasePointerCapture(ev.pointerId);
    } catch {
      /* ignore */
    }
    dragRef.current = { ...d, active: false, pointerId: null };

    if (!d.moved) {
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(x, y, scale, tx, ty);
      const posMap = getPositionsForFrame();
      const nodeId = hitTestWorld(world.x, world.y, posMap);
      if (nodeId) {
        onSelectEdge?.("");
        onSelectNode?.(nodeId);
      } else {
        const edgeId = hitTestClosestEdgeId(x, y, posMap, scale, tx, ty);
        if (edgeId) {
          onSelectNode?.("");
          onSelectEdge?.(edgeId);
        } else {
          onSelectNode?.("");
          onSelectEdge?.("");
        }
      }
    } else {
      queueHoverPick(ev.clientX, ev.clientY);
    }
  }

  function handleCenterOnSelected() {
    if (!selectedNodeId) return;
    const { w, h } = getViewportDims();
    const positions = getPositionsForFrame();
    const pw = positions.get(selectedNodeId);
    if (!pw) return;
    const { scale } = transformRef.current;
    const next = {
      scale,
      tx: w / 2 - pw.x * scale,
      ty: h / 2 - pw.y * scale,
    };
    transformRef.current = next;
    setTransform(next);
  }

  function handleResetView() {
    applyFit();
  }

  /** Set scale to 1 while keeping the world point under the viewport center fixed. */
  function handleResetZoom() {
    const { w, h } = getViewportDims();
    const cx = w / 2;
    const cy = h / 2;
    const { scale, tx, ty } = transformRef.current;
    const world = screenToWorld(cx, cy, scale, tx, ty);
    const newScale = 1;
    const next = {
      scale: newScale,
      tx: cx - world.x * newScale,
      ty: cy - world.y * newScale,
    };
    transformRef.current = next;
    setTransform(next);
  }

  function handleKeyDown(ev) {
    if (ev.key === "Escape") {
      ev.preventDefault();
      onSelectNode?.("");
      onSelectEdge?.("");
      return;
    }
    const el = ev.target;
    if (
      el &&
      (String(el.tagName).toUpperCase() === "INPUT" ||
        String(el.tagName).toUpperCase() === "TEXTAREA" ||
        el.isContentEditable)
    ) {
      return;
    }
    if (ev.key === "+" || ev.key === "=") {
      ev.preventDefault();
      zoomAtViewportCenter(1.08);
      return;
    }
    if (ev.key === "-" || ev.key === "_") {
      ev.preventDefault();
      zoomAtViewportCenter(0.92);
      return;
    }
    if (ev.key === "0" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
      ev.preventDefault();
      applyFit();
    }
  }

  if (graph.nodes.length === 0) {
    return (
      <Box
        component="section"
        role="region"
        aria-label="Graph canvas"
        sx={{
          borderRadius: "6px",
          border: "1px solid rgba(255,255,255,0.08)",
          backgroundColor: "#1a1a1a",
          minHeight: MIN_CANVAS_HEIGHT,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
        }}
      >
        <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.5)" }}>No nodes to draw on canvas.</Typography>
      </Box>
    );
  }

  const selectionLive = selectedEdgeId
    ? `Selected edge ${selectedEdgeId}.`
    : selectedNodeId
      ? `Selected node ${selectedNodeId}.`
      : "No node or edge selected.";

  const simStatus =
    layoutMode === "force" ? (isSimulationStable ? "Layout stable." : "Layout simulating.") : "";

  const canvasHelpTitle = (
    <Box component="span" sx={{ display: "block", maxWidth: 340, fontSize: "0.75rem", lineHeight: 1.45, fontWeight: 400 }}>
      Wheel over the canvas zooms. Drag empty canvas to pan. Click a node or edge to select. Escape clears selection (focus the
      graph first). Keys + / − / 0 zoom and fit when the graph has focus.
      {layoutMode === "force"
        ? " Force: drag a node; after layout stabilizes, release to pin. Restart respreads; Unpin releases pins."
        : " Circle: static ring — drag a node to switch to Force."}
    </Box>
  );

  return (
    <Box
      ref={wrapRef}
      component="section"
      role="region"
      aria-label="Graph canvas"
      aria-describedby="graph-canvas-live"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      sx={{
        width: "100%",
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        borderRadius: "6px",
        border: "1px solid rgba(255,255,255,0.08)",
        overflow: "hidden",
        backgroundColor: "#0a0a0a",
        position: "relative",
        outline: "none",
        alignSelf: "stretch",
        "&:focus-visible": {
          boxShadow: "0 0 0 1px rgba(99, 102, 241, 0.5)",
        },
      }}
    >
      <Typography
        id="graph-canvas-live"
        component="span"
        aria-live="polite"
        sx={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0,0,0,0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {selectionLive}
        {simStatus ? ` ${simStatus}` : ""}
      </Typography>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.75,
          px: 1,
          py: 0.5,
          flexShrink: 0,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <Tooltip title={canvasHelpTitle} placement="bottom" enterDelay={300}>
          <CursorIconButton type="button" aria-label="Canvas controls help">
            <InfoOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconButton>
        </Tooltip>
        {layoutMode === "force" ? (
          <Box sx={{ width: 120, minWidth: 100, maxWidth: 140, px: 0.25 }}>
            <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.42)", mb: 0.15 }}>
              Repulsion {Math.round(repulsionPercent)}%
            </Typography>
            <Slider
              size="small"
              value={repulsionPercent}
              min={0}
              max={100}
              step={1}
              onChange={(_, v) => setRepulsionPercent(v)}
              getAriaValueText={() => `${Math.round(repulsionPercent)} percent`}
              sx={{
                color: "rgba(129,140,248,0.85)",
                py: 0,
                "& .MuiSlider-thumb": { width: 10, height: 10 },
                "& .MuiSlider-track": { border: "none" },
              }}
              aria-label="Force layout repulsion strength"
            />
          </Box>
        ) : null}
        {layoutMode === "force" ? (
          <>
            <Tooltip title="Restart simulation (reseed + rerun physics)" placement="bottom" enterDelay={300}>
              <CursorIconButton type="button" onClick={handleRestartForceSimulation} aria-label="Restart simulation">
                <RestartAltOutlinedIcon sx={{ fontSize: "1.05rem" }} />
              </CursorIconButton>
            </Tooltip>
            <Tooltip title="Unpin all nodes" placement="bottom" enterDelay={300}>
              <span>
                <CursorIconButton type="button" onClick={handleUnpinAll} disabled={pinnedNodeCount === 0} aria-label="Unpin all nodes">
                  <LinkOffOutlinedIcon sx={{ fontSize: "1.05rem" }} />
                </CursorIconButton>
              </span>
            </Tooltip>
          </>
        ) : null}
        <Box sx={{ flex: 1, minWidth: 4 }} />
        <Tooltip title="Fit graph to view" placement="bottom">
          <CursorIconButton type="button" onClick={handleResetView} aria-label="Fit graph to view">
            <FitScreenOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconButton>
        </Tooltip>
        <Tooltip title="Reset zoom (scale 1 at center)" placement="bottom">
          <CursorIconButton type="button" onClick={handleResetZoom} aria-label="Reset zoom">
            <ZoomOutMapOutlinedIcon sx={{ fontSize: "1.05rem" }} />
          </CursorIconButton>
        </Tooltip>
        <Tooltip title="Center viewport on selected node" placement="bottom">
          <span>
            <CursorIconButton
              type="button"
              onClick={handleCenterOnSelected}
              disabled={!selectedNodeId}
              aria-label="Center on selected node"
            >
              <CenterFocusStrongOutlinedIcon sx={{ fontSize: "1.05rem" }} />
            </CursorIconButton>
          </span>
        </Tooltip>
      </Box>
      <Box
        ref={canvasHostRef}
        sx={{
          flex: 1,
          minHeight: MIN_CANVAS_HEIGHT,
          minWidth: 0,
          position: "relative",
          display: "block",
        }}
      >
        <canvas
          ref={canvasRef}
          aria-label="Interactive graph: pan and zoom with pointer; click a node or edge to select it."
          onPointerDown={handlePointerDown}
          onPointerMove={handleCanvasPointerMove}
          onPointerLeave={handleCanvasPointerLeave}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          style={{
            display: "block",
            width: "100%",
            height: "100%",
            cursor: canvasCursor,
            touchAction: "none",
            verticalAlign: "top",
          }}
        />
      </Box>
    </Box>
  );
}
