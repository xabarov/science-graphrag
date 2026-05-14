/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from "vitest";

import { graphCanvasInputPointerMove } from "./pointerMove.js";

describe("graphCanvasInputPointerMove", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });
  it("marks node drag moved and reheats physics after drag threshold", () => {
    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };
    const nodeDragRef = { current: { active: true, moved: false, nodeId: "n1", startX: 0, startY: 0, pointerId: 1 } };
    const dragRef = { current: { active: false, moved: false } };
    const draggedNodePositionRef = { current: null };
    const simNodesRef = { current: [{ id: "n1", x: 0, y: 0 }] };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const bumpPhysicsReheat = vi.fn();
    const setIsSimulationStable = vi.fn();
    const setHoveredNodeId = vi.fn();
    const setHoveredEdgeId = vi.fn();
    const setCanvasCursor = vi.fn();
    const queueHoverPick = vi.fn();
    const invokeCanvasRedraw = vi.fn();
    const setTransform = vi.fn();

    graphCanvasInputPointerMove(
      {
        canvasRef,
        nodeDragRef,
        dragRef,
        draggedNodePositionRef,
        simNodesRef,
        transformRef,
        setTransform,
        setIsSimulationStable,
        bumpPhysicsReheat,
        setHoveredNodeId,
        setHoveredEdgeId,
        setCanvasCursor,
        queueHoverPick,
        invokeCanvasRedraw,
      },
      /** @type {PointerEvent} */ ({ clientX: 10, clientY: 10 }),
    );

    expect(nodeDragRef.current.moved).toBe(true);
    expect(setHoveredNodeId).toHaveBeenCalledWith("");
    expect(setHoveredEdgeId).toHaveBeenCalledWith("");
    expect(setCanvasCursor).toHaveBeenCalledWith("grabbing");
    expect(setIsSimulationStable).toHaveBeenCalledWith(false);
    expect(bumpPhysicsReheat).toHaveBeenCalledTimes(1);
    expect(invokeCanvasRedraw).toHaveBeenCalled();
    expect(queueHoverPick).not.toHaveBeenCalled();
  });

  it("applies pan translate when pan drag has moved", () => {
    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };
    const nodeDragRef = { current: { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null } };
    const dragRef = { current: { active: true, moved: true, startX: 0, startY: 0, startTx: 1, startTy: 2, pointerId: 1 } };
    const draggedNodePositionRef = { current: null };
    const simNodesRef = { current: [] };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const setTransform = vi.fn();

    graphCanvasInputPointerMove(
      {
        canvasRef,
        nodeDragRef,
        dragRef,
        draggedNodePositionRef,
        simNodesRef,
        transformRef,
        setTransform,
        setIsSimulationStable: vi.fn(),
        bumpPhysicsReheat: vi.fn(),
        setHoveredNodeId: vi.fn(),
        setHoveredEdgeId: vi.fn(),
        setCanvasCursor: vi.fn(),
        queueHoverPick: vi.fn(),
        invokeCanvasRedraw: vi.fn(),
      },
      /** @type {PointerEvent} */ ({ clientX: 5, clientY: 6 }),
    );

    expect(transformRef.current).toEqual({ scale: 1, tx: 6, ty: 8 });
    expect(setTransform).toHaveBeenCalledWith({ scale: 1, tx: 6, ty: 8 });
  });

  it("queues hover pick when no drag session is active", () => {
    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0 });
    const canvasRef = { current: canvas };
    const nodeDragRef = { current: { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null } };
    const dragRef = { current: { active: false, moved: false, startX: 0, startY: 0, startTx: 0, startTy: 0, pointerId: null } };
    const queueHoverPick = vi.fn();

    graphCanvasInputPointerMove(
      {
        canvasRef,
        nodeDragRef,
        dragRef,
        draggedNodePositionRef: { current: null },
        simNodesRef: { current: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        setTransform: vi.fn(),
        setIsSimulationStable: vi.fn(),
        bumpPhysicsReheat: vi.fn(),
        setHoveredNodeId: vi.fn(),
        setHoveredEdgeId: vi.fn(),
        setCanvasCursor: vi.fn(),
        queueHoverPick,
        invokeCanvasRedraw: vi.fn(),
      },
      /** @type {PointerEvent} */ ({ clientX: 12, clientY: 34 }),
    );

    expect(queueHoverPick).toHaveBeenCalledWith(12, 34);
  });
});
