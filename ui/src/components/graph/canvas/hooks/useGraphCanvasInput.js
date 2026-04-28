import { useCallback, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { screenToWorld } from "../graphCanvasTransform.js";
import { hitTestClosestEdgeId, hitTestNodeScreen } from "../graphCanvasDraw.js";
import { dispatchGraphCanvasPointerDown, dispatchGraphCanvasPointerUp } from "../graphCanvasPointerEvents.js";
import { useGraphPhysicsPointerBridge } from "../GraphPhysicsPointerBridgeContext.jsx";
import { writeSimNodeWorldPosition } from "../graphCanvasSimBuffer.js";

const DRAG_THRESHOLD_PX = 5;

/**
 * Canvas pointer wiring for {@link GraphCanvasMvp}.
 *
 * @param {object} opts
 * @param {import("react").MutableRefObject<import("../graphSimulationAdapter.js").SimNode[]>} opts.simNodesRef Live sim buffer for force mode (mutated on drag).
 * @param {() => void} opts.invokeCanvasRedraw Repaint canvas without waiting for React (physics rAF + drag moves).
 */
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
  setSimNodes,
  isSimulationStable,
  setIsSimulationStable,
  bumpPhysicsReheat,
  draggedNodePositionRef,
  fixedNodesRef,
  setPinnedNodeCount,
  resolveNodeCanvasLabel,
  graphColorBy = "type",
  selectedNodeId = "",
  searchActive = false,
  searchMatchSet = null,
  simNodesRef,
  invokeCanvasRedraw,
}) {
  const [hoveredNodeId, setHoveredNodeId] = useState("");
  const [hoveredEdgeId, setHoveredEdgeId] = useState("");
  const [canvasCursor, setCanvasCursor] = useState("grab");
  const physicsPointerBridge = useGraphPhysicsPointerBridge();
  const pointerBus = physicsPointerBridge?.pointerBus;

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
          hitTestNodeScreen(lx, ly, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel, {
            colorBy: graphColorBy,
            nodeCount: graph.nodes.length,
            searchActive,
            searchMatchSet: searchMatchSet instanceof Set ? searchMatchSet : null,
            selectedNodeId,
            hoveredNodeId,
          }) || "";
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
    [
      canvasRef,
      getPositionsForFrame,
      graph.edges,
      graph.nodes,
      graphColorBy,
      hoveredNodeId,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      transformRef,
    ],
  );

  const handlePointerDown = useCallback(
    (ev) => {
      if (ev.button !== 0) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      dispatchGraphCanvasPointerDown(pointerBus);
      const rect = canvas.getBoundingClientRect();
      const x = ev.clientX - rect.left;
      const y = ev.clientY - rect.top;
      const { scale, tx, ty } = transformRef.current;
      if (simNodesRef.current.length > 0) {
        const posMap = getPositionsForFrame();
        const nodeId = hitTestNodeScreen(x, y, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel, {
          colorBy: graphColorBy,
          nodeCount: graph.nodes.length,
          searchActive,
          searchMatchSet: searchMatchSet instanceof Set ? searchMatchSet : null,
          selectedNodeId,
          hoveredNodeId,
        });
        if (nodeId) {
          if (layoutMode === "circle" && onCanvasLayoutModeChange) flushSync(() => onCanvasLayoutModeChange("force"));
          const world = screenToWorld(x, y, scale, tx, ty);
          canvas.setPointerCapture(ev.pointerId);
          nodeDragRef.current = { active: true, moved: false, nodeId, startX: x, startY: y, pointerId: ev.pointerId };
          draggedNodePositionRef.current = { id: nodeId, x: world.x, y: world.y };
          writeSimNodeWorldPosition(simNodesRef.current, nodeId, world.x, world.y);
          invokeCanvasRedraw();
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
      graphColorBy,
      hoveredNodeId,
      layoutMode,
      onCanvasLayoutModeChange,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      simNodesRef,
      invokeCanvasRedraw,
      transformRef,
      pointerBus,
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
        writeSimNodeWorldPosition(simNodesRef.current, nd.nodeId, world.x, world.y);
        invokeCanvasRedraw();
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
    [
      bumpPhysicsReheat,
      canvasRef,
      draggedNodePositionRef,
      queueHoverPick,
      setIsSimulationStable,
      setTransform,
      simNodesRef,
      invokeCanvasRedraw,
      transformRef,
    ],
  );

  const handlePointerLeave = useCallback(() => {
    setHoveredNodeId("");
    setHoveredEdgeId("");
    setCanvasCursor("grab");
  }, []);

  const handlePointerUp = useCallback(
    (ev) => {
      try {
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
          if (moved) {
            setSimNodes(simNodesRef.current.map((n) => ({ ...n })));
            invokeCanvasRedraw();
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
          const nodeId = hitTestNodeScreen(x, y, graph.nodes, posMap, transformRef.current, resolveNodeCanvasLabel, {
            colorBy: graphColorBy,
            nodeCount: graph.nodes.length,
            searchActive,
            searchMatchSet: searchMatchSet instanceof Set ? searchMatchSet : null,
            selectedNodeId,
            hoveredNodeId,
          });
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
      } finally {
        dispatchGraphCanvasPointerUp(pointerBus);
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
      graphColorBy,
      hoveredNodeId,
      isSimulationStable,
      onCanvasClick,
      onEdgeClick,
      onNodeClick,
      queueHoverPick,
      resolveNodeCanvasLabel,
      searchActive,
      searchMatchSet,
      selectedNodeId,
      setIsSimulationStable,
      setPinnedNodeCount,
      setSimNodes,
      simNodesRef,
      invokeCanvasRedraw,
      transformRef,
      pointerBus,
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
