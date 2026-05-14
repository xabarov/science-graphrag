/** @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from "vitest";

import * as pointerEvents from "../../graphCanvasPointerEvents.js";
import { graphCanvasInputPointerUp } from "./pointerUp.js";

describe("graphCanvasInputPointerUp", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });
  it("dispatches pointer-up even when no drag session is active", () => {
    const spy = vi.spyOn(pointerEvents, "dispatchGraphCanvasPointerUp").mockImplementation(() => {});
    const canvas = document.createElement("canvas");
    canvas.releasePointerCapture = vi.fn();
    const canvasRef = { current: canvas };
    const nodeDragRef = { current: { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null } };
    const dragRef = { current: { active: false, moved: false, startX: 0, startY: 0, startTx: 0, startTy: 0, pointerId: null } };

    graphCanvasInputPointerUp(
      {
        canvasRef,
        nodeDragRef,
        dragRef,
        draggedNodePositionRef: { current: null },
        simNodesRef: { current: [] },
        fixedNodesRef: { current: new Set() },
        isSimulationStable: false,
        setIsSimulationStable: vi.fn(),
        bumpPhysicsReheat: vi.fn(),
        setSimNodes: vi.fn(),
        setPinnedNodeCount: vi.fn(),
        invokeCanvasRedraw: vi.fn(),
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [], edges: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
        onNodeClick: vi.fn(),
        onEdgeClick: vi.fn(),
        onCanvasClick: vi.fn(),
        queueHoverPick: vi.fn(),
        pointerBus: undefined,
      },
      /** @type {PointerEvent} */ ({ clientX: 0, clientY: 0, pointerId: 1 }),
    );

    expect(spy).toHaveBeenCalledTimes(1);
  });

  it("queues hover refresh after pan drag with movement", () => {
    vi.spyOn(pointerEvents, "dispatchGraphCanvasPointerUp").mockImplementation(() => {});
    const queueHoverPick = vi.fn();
    const canvas = document.createElement("canvas");
    canvas.releasePointerCapture = vi.fn();
    const canvasRef = { current: canvas };
    const nodeDragRef = { current: { active: false, moved: false, nodeId: "", startX: 0, startY: 0, pointerId: null } };
    const dragRef = { current: { active: true, moved: true, startX: 0, startY: 0, startTx: 0, startTy: 0, pointerId: 1 } };

    graphCanvasInputPointerUp(
      {
        canvasRef,
        nodeDragRef,
        dragRef,
        draggedNodePositionRef: { current: null },
        simNodesRef: { current: [] },
        fixedNodesRef: { current: new Set() },
        isSimulationStable: false,
        setIsSimulationStable: vi.fn(),
        bumpPhysicsReheat: vi.fn(),
        setSimNodes: vi.fn(),
        setPinnedNodeCount: vi.fn(),
        invokeCanvasRedraw: vi.fn(),
        getPositionsForFrame: () => new Map(),
        graph: { nodes: [], edges: [] },
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        hoveredNodeId: "",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
        onNodeClick: vi.fn(),
        onEdgeClick: vi.fn(),
        onCanvasClick: vi.fn(),
        queueHoverPick,
        pointerBus: undefined,
      },
      /** @type {PointerEvent} */ ({ clientX: 20, clientY: 30, pointerId: 1 }),
    );

    expect(queueHoverPick).toHaveBeenCalledWith(20, 30);
  });
});
