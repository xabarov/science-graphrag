import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { CursorSmallButton } from "../common/index.js";
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
/** Minimum drawing height before container measurement (matches workspace column expectations). */
const MIN_CANVAS_HEIGHT = 280;

/**
 * Phase 4.2–4.3: canvas with world coords, zoom/pan, fit/reset/center, keyboard (Escape).
 * @param {{
 *   graph: { nodes: Array<{ id: string }>, edges: Array<{ source: string, target: string, id?: string }> },
 *   selectedNodeId: string,
 *   selectedEdgeId?: string,
 *   onSelectNode?: (nodeId: string) => void,
 *   onSelectEdge?: (edgeId: string) => void,
 * }} props
 */
export default function GraphCanvasMvp({
  graph,
  selectedNodeId,
  selectedEdgeId = "",
  onSelectNode,
  onSelectEdge,
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

  const layoutKey = useMemo(() => graph.nodes.map((n) => n.id).join("\0"), [graph.nodes]);
  const layoutWorldRadius = useMemo(() => worldRadiusForNodeCount(graph.nodes.length), [graph.nodes.length]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);

  const getViewportDims = useCallback(() => {
    const host = canvasHostRef.current;
    const w = Math.max(1, hostSize.width || host?.clientWidth || 1);
    const h = Math.max(MIN_CANVAS_HEIGHT, hostSize.height || host?.clientHeight || MIN_CANVAS_HEIGHT);
    return { w, h };
  }, [hostSize.height, hostSize.width]);

  const applyFit = useCallback(() => {
    if (graph.nodes.length === 0) return;
    const { w, h } = getViewportDims();
    const positions = computeWorldLayout(graph.nodes, layoutWorldRadius);
    positionsRef.current = positions;
    const next = computeFitTransform(positions, w, h, NODE_RADIUS, FIT_PADDING);
    transformRef.current = next;
    setTransform(next);
  }, [getViewportDims, graph.nodes, layoutWorldRadius]);

  useEffect(() => {
    transformRef.current = transform;
  }, [transform]);

  useEffect(() => {
    let raf = 0;
    raf = requestAnimationFrame(() => {
      applyFit();
    });
    return () => cancelAnimationFrame(raf);
  }, [layoutKey, applyFit]);

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
    const positions = computeWorldLayout(graph.nodes, layoutWorldRadius);
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

    ctx.font = EDGE_LABEL_FONT;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const edgesForLabels = [...graph.edges].sort((a, b) => {
      const rank = (e) => (e.id === hoveredEdgeId || e.id === selectedEdgeId ? 1 : 0);
      return rank(a) - rank(b);
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

    for (const node of nodeById.values()) {
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

    ctx.font = LABEL_FONT;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const node of nodeById.values()) {
      const pw = positions.get(node.id);
      if (!pw) continue;
      const p = worldToScreen(pw.x, pw.y, scale, tx, ty);
      const sel = node.id === selectedNodeId;
      const rawLabel = node.label != null && String(node.label).trim() ? node.label : node.id;
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
    getViewportDims,
    graph.edges,
    graph.nodes,
    hoveredEdgeId,
    hoveredNodeId,
    layoutWorldRadius,
    nodeById,
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

  function hitTestWorld(wx, wy) {
    const positions = positionsRef.current;
    for (const node of nodeById.values()) {
      const p = positions.get(node.id);
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
      const rect = canvas.getBoundingClientRect();
      const lx = cx - rect.left;
      const ly = cy - rect.top;
      const { scale, tx, ty } = transformRef.current;
      const world = screenToWorld(lx, ly, scale, tx, ty);
      const nodeId = hitTestWorld(world.x, world.y) ?? "";
      if (nodeId) {
        setHoveredNodeId((prev) => (prev === nodeId ? prev : nodeId));
        setHoveredEdgeId("");
        setCanvasCursor("pointer");
        return;
      }
      setHoveredNodeId("");
      const positions = computeWorldLayout(graph.nodes, layoutWorldRadius);
      const edgeId = hitTestClosestEdgeId(lx, ly, positions, scale, tx, ty);
      setHoveredEdgeId((prev) => (prev === edgeId ? prev : edgeId));
      setCanvasCursor(edgeId ? "pointer" : "grab");
    });
  }

  function handlePointerDown(ev) {
    if (ev.button !== 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.setPointerCapture(ev.pointerId);
    const rect = canvas.getBoundingClientRect();
    const x = ev.clientX - rect.left;
    const y = ev.clientY - rect.top;
    const { tx, ty } = transformRef.current;
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
    const d = dragRef.current;
    if (d.active) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const dx = x - d.startX;
      const dy = y - d.startY;
      if (!d.moved && (dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX)) {
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
    const d = dragRef.current;
    if (!d.active) return;
    const canvas = canvasRef.current;
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
      const nodeId = hitTestWorld(world.x, world.y);
      if (nodeId) {
        onSelectEdge?.("");
        onSelectNode?.(nodeId);
      } else {
        const positions = computeWorldLayout(graph.nodes, layoutWorldRadius);
        const edgeId = hitTestClosestEdgeId(x, y, positions, scale, tx, ty);
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
    const positions = positionsRef.current;
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
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, px: 1.5, pt: 1, pb: 0.5, flexShrink: 0 }}>
        <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)", flex: "1 1 140px" }}>
          Wheel over the canvas zooms in/out (page scroll works when the cursor is outside this area). Drag to pan · click a node
          or edge to select · Escape clears selection (focus graph first). Use &quot;Center on selected&quot; to align the viewport on a
          node.
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75 }}>
          <CursorSmallButton type="button" onClick={handleResetView}>
            Fit
          </CursorSmallButton>
          <CursorSmallButton type="button" onClick={handleResetZoom}>
            Reset zoom
          </CursorSmallButton>
          <CursorSmallButton type="button" onClick={handleCenterOnSelected} disabled={!selectedNodeId}>
            Center on selected
          </CursorSmallButton>
        </Box>
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
