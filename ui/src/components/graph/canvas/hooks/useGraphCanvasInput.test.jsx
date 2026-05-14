/** @vitest-environment jsdom */
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as graphCanvasDraw from "../graphCanvasDraw.js";
import * as pointerEvents from "../graphCanvasPointerEvents.js";
import { GraphPhysicsPointerBridgeProvider } from "../GraphPhysicsPointerBridgeContext.jsx";
import useGraphCanvasInput from "./useGraphCanvasInput.js";

function wrapper({ children }) {
  return <GraphPhysicsPointerBridgeProvider>{children}</GraphPhysicsPointerBridgeProvider>;
}

describe("useGraphCanvasInput", () => {
  let canvasRef;
  let transformRef;
  let simNodesRef;
  let draggedNodePositionRef;
  let fixedNodesRef;
  let setTransform;
  let onNodeClick;
  let onEdgeClick;
  let onCanvasClick;
  let setSimNodes;
  let setIsSimulationStable;
  let bumpPhysicsReheat;
  let setPinnedNodeCount;
  let invokeCanvasRedraw;

  beforeEach(() => {
    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 600, height: 400, right: 600, bottom: 400 });
    canvas.setPointerCapture = vi.fn();
    canvas.releasePointerCapture = vi.fn();
    canvasRef = { current: canvas };
    transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    simNodesRef = { current: [] };
    draggedNodePositionRef = { current: null };
    fixedNodesRef = { current: new Set() };
    setTransform = vi.fn((next) => {
      transformRef.current = typeof next === "function" ? next(transformRef.current) : next;
    });
    onNodeClick = vi.fn();
    onEdgeClick = vi.fn();
    onCanvasClick = vi.fn();
    setSimNodes = vi.fn();
    setIsSimulationStable = vi.fn();
    bumpPhysicsReheat = vi.fn();
    setPinnedNodeCount = vi.fn();
    invokeCanvasRedraw = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderInput(overrides = {}) {
    const {
      graph = { nodes: [], edges: [] },
      getPositionsForFrame = () => new Map(),
      layoutMode = "force",
      isSimulationStable: simStable = false,
      simNodesRef: simRef = simNodesRef,
    } = overrides;

    return renderHook(
      () =>
        useGraphCanvasInput({
          canvasRef,
          graph,
          transformRef,
          setTransform,
          onNodeClick,
          onEdgeClick,
          onCanvasClick,
          getPositionsForFrame,
          layoutMode,
          onCanvasLayoutModeChange: vi.fn(),
          setSimNodes,
          isSimulationStable: simStable,
          setIsSimulationStable,
          bumpPhysicsReheat,
          draggedNodePositionRef,
          fixedNodesRef,
          setPinnedNodeCount,
          resolveNodeCanvasLabel: () => null,
          simNodesRef: simRef,
          invokeCanvasRedraw,
        }),
      { wrapper },
    );
  }

  it("tap on empty canvas invokes onCanvasClick (pan session, no move)", async () => {
    const { result } = renderInput();
    const down = /** @type {PointerEvent} */ ({ button: 0, clientX: 10, clientY: 10, pointerId: 7 });
    const up = /** @type {PointerEvent} */ ({ button: 0, clientX: 10, clientY: 10, pointerId: 7 });

    act(() => {
      result.current.handlePointerDown(down);
    });
    act(() => {
      result.current.handlePointerUp(up);
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(onCanvasClick).toHaveBeenCalledTimes(1);
    expect(onNodeClick).not.toHaveBeenCalled();
    expect(onEdgeClick).not.toHaveBeenCalled();
  });

  it("tap after pan without move invokes onNodeClick when hit-test returns a node", async () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("n1");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("");
    const { result } = renderInput({
      graph: { nodes: [{ id: "n1", type: "Work", label: "N" }], edges: [] },
    });
    const down = /** @type {PointerEvent} */ ({ button: 0, clientX: 10, clientY: 10, pointerId: 2 });
    const up = /** @type {PointerEvent} */ ({ button: 0, clientX: 10, clientY: 10, pointerId: 2 });

    act(() => {
      result.current.handlePointerDown(down);
    });
    act(() => {
      result.current.handlePointerUp(up);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(onNodeClick).toHaveBeenCalledWith("n1");
    expect(onEdgeClick).not.toHaveBeenCalled();
    expect(onCanvasClick).not.toHaveBeenCalled();
  });

  it("tap after pan without move invokes onEdgeClick when hit-test returns an edge", async () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("e1");
    const { result } = renderInput({
      graph: { nodes: [], edges: [{ id: "e1", source: "a", target: "b" }] },
    });
    const down = /** @type {PointerEvent} */ ({ button: 0, clientX: 5, clientY: 5, pointerId: 3 });
    const up = /** @type {PointerEvent} */ ({ button: 0, clientX: 5, clientY: 5, pointerId: 3 });

    act(() => {
      result.current.handlePointerDown(down);
    });
    act(() => {
      result.current.handlePointerUp(up);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(onEdgeClick).toHaveBeenCalledWith("e1");
    expect(onNodeClick).not.toHaveBeenCalled();
    expect(onCanvasClick).not.toHaveBeenCalled();
  });

  it("releases node drag without move invokes onNodeClick (same path as tap)", async () => {
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("n1");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("");
    const simWithNode = { current: [{ id: "n1" }] };
    const { result } = renderInput({
      graph: { nodes: [{ id: "n1", type: "Work", label: "N" }], edges: [] },
      simNodesRef: simWithNode,
    });
    const ev = /** @type {PointerEvent} */ ({ button: 0, clientX: 40, clientY: 40, pointerId: 9 });

    act(() => {
      result.current.handlePointerDown(ev);
    });
    act(() => {
      result.current.handlePointerUp(ev);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(onNodeClick).toHaveBeenCalledWith("n1");
  });

  it("dispatches pointer-up in finally after pan tap (matches onPointerCancel wiring)", async () => {
    const upSpy = vi.spyOn(pointerEvents, "dispatchGraphCanvasPointerUp").mockImplementation(() => {});
    const { result } = renderInput();
    const ev = /** @type {PointerEvent} */ ({ button: 0, clientX: 8, clientY: 8, pointerId: 4 });

    act(() => {
      result.current.handlePointerDown(ev);
    });
    act(() => {
      result.current.handlePointerUp(ev);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(upSpy).toHaveBeenCalledTimes(1);
  });
});
