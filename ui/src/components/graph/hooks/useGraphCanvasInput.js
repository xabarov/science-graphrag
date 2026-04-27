import { useCallback, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { screenToWorld } from "../graphCanvasTransform.js";
import { hitTestClosestEdgeId, hitTestNodeScreen } from "../graphCanvasDraw.js";

const DRAG_THRESHOLD_PX = 5;
export default function useGraphCanvasInput({
  canvasRef,
  graph,
  transformRef,
  setTransform,
  onNodeClick,
  onEdgeClick,
  onCanvasClick,
  getPositionsForFrame,
  layoutMode,
  onCanvasLayoutModeChange,
  simNodes,
  setSimNodes,
  isSimulationStable,
  setIsSimulationStable,
  bumpPhysicsReheat,
  draggedNodePositionRef,
  fixedNodesRef,
  setPinnedNodeCount,
  resolveNodeCanvasLabel,
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [hoveredEdgeId, setHoveredEdgeId] = useState("");
  const [canvasCursor, setCanvasCursor] = useState("grab");
  const hoverPickPendingRef = useRef(false);
  const hoverClientRef = useRef({ x: 0, y: 0 });
  const dragRef = useRef({ active: false, moved: false, startX: 0, startY: 0, startTx: 0, startTy: 0, pointerId: null });
  const nodeDragRef = useRef({ active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null });

  const queueHoverPick = useCallback(
    (clientX, clientY) => {
      hoverClientRef.current = { x: clientX, y: clientY };
      if (hoverPickPendingRef.current) return;
      hoverPickPendingRef.current = true;
      requestAnimationFrame(() => {
        hoverPickPendingRef.current = false;
        const canvas = canvasRef.current;
        if (!canvas) return;
        if (dragRef.current.active && dragRef.current.moved) return;
        if (nodeDragRef.current.active && nodeDragRef.current.moved) return;
        const rect = canvas.getBoundingClientRect();
        const lx = hoverClientRef.current.x - rect.left;
        const ly = hoverClientRef.current.y - rect.top;
        const posMap = getPositionsForFrame();
        const nodeId =
          hitTestNodeScreen(lx, ly, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel) || "";
        if (nodeId) {
          setHoveredNodeId((prev) => (prev === nodeId ? prev : nodeId));
          setHoveredEdgeId("");
          setCanvasCursor("pointer");
          return;
        }
        setHoveredNodeId("");
        const edgeId = hitTestClosestEdgeId(lx, ly, graph.edges, posMap, transformRef.current);
        setHoveredEdgeId((prev) => (prev === edgeId ? prev : edgeId));
        setCanvasCursor(edgeId ? "pointer" : "grab");
      });
    },
    [canvasRef, getPositionsForFrame, graph.edges, graph.nodes, resolveNodeCanvasLabel, transformRef],
  );

  const handlePointerDown = useCallback(
    (ev) => {
      if (ev.button !== 0) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      if (simNodes.length > 0) {
        const posMap = getPositionsForFrame();
        const nodeId = hitTestNodeScreen(x, y, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel);
        if (nodeId) {
          if (layoutMode === "circle" && onCanvasLayoutModeChange) flushSync(() => onCanvasLayoutModeChange("force"));
          const world = screenToWorld(x, y, scale, tx, ty);
          canvas.setPointerCapture(ev.pointerId);
          nodeDragRef.current = { active: true, moved: false, nodeId, startX: x, startY: y, pointerId: ev.pointerId };
          draggedNodePositionRef.current = { id: nodeId, x: world.x, y: world.y };
          setSimNodes((prev) => prev.map((n) => (n.id === nodeId ? { ...n, x: world.x, y: world.y, vx: 0, vy: 0 } : n)));
          return;
        }
      }
      canvas.setPointerCapture(ev.pointerId);
      dragRef.current = { active: true, moved: false, startX: x, startY: y, startTx: tx, startTy: ty, pointerId: ev.pointerId };
    },
    [
      canvasRef,
      draggedNodePositionRef,
      getPositionsForFrame,
      graph.nodes,
      layoutMode,
      onCanvasLayoutModeChange,
      resolveNodeCanvasLabel,
      setSimNodes,
      simNodes.length,
      transformRef,
    ],
  );

  const handlePointerMove = useCallback(
    (ev) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const nd = nodeDragRef.current;
      if (nd.active) {
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
        const world = screenToWorld(x, y, transformRef.current.scale, transformRef.current.tx, transformRef.current.ty);
        draggedNodePositionRef.current = { id: nd.nodeId, x: world.x, y: world.y };
        setSimNodes((prev) => prev.map((n) => (n.id === nd.nodeId ? { ...n, x: world.x, y: world.y, vx: 0, vy: 0 } : n)));
        return;
      }
      const d = dragRef.current;
      if (d.active) {
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
    },
    [bumpPhysicsReheat, canvasRef, draggedNodePositionRef, queueHoverPick, setIsSimulationStable, setSimNodes, setTransform, transformRef],
  );

  const handlePointerLeave = useCallback(() => {
    setHoveredNodeId("");
    setHoveredEdgeId("");
    setCanvasCursor("grab");
  }, []);

  const handlePointerUp = useCallback(
    (ev) => {
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
        nodeDragRef.current = { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null };
        draggedNodePositionRef.current = null;
        if (moved) {
          setIsSimulationStable(false);
          bumpPhysicsReheat();
        }
        if (pinAfterDrop) {
          fixedNodesRef.current.add(nodeId);
          setPinnedNodeCount(fixedNodesRef.current.size);
        }
        if (!moved) queueMicrotask(() => onNodeClick?.(nodeId));
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
        const posMap = getPositionsForFrame();
        const nodeId = hitTestNodeScreen(x, y, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel);
        if (nodeId) {
          queueMicrotask(() => onNodeClick?.(nodeId));
          return;
        }
        const edgeId = hitTestClosestEdgeId(x, y, graph.edges, posMap, transformRef.current);
        if (edgeId) {
          queueMicrotask(() => onEdgeClick?.(edgeId));
          return;
        }
        queueMicrotask(() => onCanvasClick?.());
      } else {
        queueHoverPick(ev.clientX, ev.clientY);
      }
    },
    [
      bumpPhysicsReheat,
      canvasRef,
      draggedNodePositionRef,
      fixedNodesRef,
      getPositionsForFrame,
      graph.edges,
      graph.nodes,
      isSimulationStable,
      onCanvasClick,
      onEdgeClick,
      onNodeClick,
      queueHoverPick,
      resolveNodeCanvasLabel,
      setIsSimulationStable,
      setPinnedNodeCount,
      transformRef,
    ],
  );

  return {
    hoveredNodeId,
    hoveredEdgeId,
    canvasCursor,
    queueHoverPick,
    handlePointerDown,
    handlePointerMove,
    handlePointerLeave,
    handlePointerUp,
    clearHover: () => {
      setHoveredNodeId("");
      setHoveredEdgeId("");
      setCanvasCursor("grab");
    },
  };
}
