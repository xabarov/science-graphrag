/** @vitest-environment jsdom */
import { renderHook, act } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as graphCanvasDraw from "../../graphCanvasDraw.js";
import { useGraphCanvasInputHoverPick } from "./hoverPick.js";

describe("useGraphCanvasInputHoverPick", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("skips hit-test in RAF when pan drag is active and moved", async () => {
    vi.stubGlobal("requestAnimationFrame", (cb) => {
      queueMicrotask(() => cb(0));
      return 1;
    });
    const hitSpy = vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 });
    const canvasRef = { current: canvas };
    const dragRef = { current: { active: true, moved: true } };
    const nodeDragRef = { current: { active: false, moved: false } };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const getPositionsForFrame = () => new Map();

    const { result } = renderHook(() =>
      useGraphCanvasInputHoverPick({
        canvasRef,
        dragRef,
        nodeDragRef,
        getPositionsForFrame,
        graph: { nodes: [], edges: [] },
        transformRef,
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      }),
    );

    act(() => {
      result.current.queueHoverPick(10, 10);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(hitSpy).not.toHaveBeenCalled();
  });

  it("skips hit-test in RAF when node drag is active and moved", async () => {
    vi.stubGlobal("requestAnimationFrame", (cb) => {
      queueMicrotask(() => cb(0));
      return 1;
    });
    const hitSpy = vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 });
    const canvasRef = { current: canvas };
    const dragRef = { current: { active: false, moved: false } };
    const nodeDragRef = { current: { active: true, moved: true } };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const getPositionsForFrame = () => new Map();

    const { result } = renderHook(() =>
      useGraphCanvasInputHoverPick({
        canvasRef,
        dragRef,
        nodeDragRef,
        getPositionsForFrame,
        graph: { nodes: [], edges: [] },
        transformRef,
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      }),
    );

    act(() => {
      result.current.queueHoverPick(10, 10);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(hitSpy).not.toHaveBeenCalled();
  });

  it("runs hit-test when pan drag is active but not yet moved (hover during press)", async () => {
    vi.stubGlobal("requestAnimationFrame", (cb) => {
      queueMicrotask(() => cb(0));
      return 1;
    });
    vi.spyOn(graphCanvasDraw, "hitTestNodeScreen").mockReturnValue("");
    vi.spyOn(graphCanvasDraw, "hitTestClosestEdgeId").mockReturnValue("");

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 });
    const canvasRef = { current: canvas };
    const dragRef = { current: { active: true, moved: false } };
    const nodeDragRef = { current: { active: false, moved: false } };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const getPositionsForFrame = () => new Map();

    const { result } = renderHook(() =>
      useGraphCanvasInputHoverPick({
        canvasRef,
        dragRef,
        nodeDragRef,
        getPositionsForFrame,
        graph: { nodes: [], edges: [] },
        transformRef,
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      }),
    );

    act(() => {
      result.current.queueHoverPick(5, 5);
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(graphCanvasDraw.hitTestNodeScreen).toHaveBeenCalled();
  });

  it("cancels scheduled hover RAF on unmount", () => {
    const cancelSpy = vi.spyOn(window, "cancelAnimationFrame");
    vi.stubGlobal("requestAnimationFrame", () => 4242);

    const canvas = document.createElement("canvas");
    canvas.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100, right: 100, bottom: 100 });
    const canvasRef = { current: canvas };
    const dragRef = { current: { active: false, moved: false } };
    const nodeDragRef = { current: { active: false, moved: false } };
    const transformRef = { current: { scale: 1, tx: 0, ty: 0 } };
    const getPositionsForFrame = () => new Map();

    const { result, unmount } = renderHook(() =>
      useGraphCanvasInputHoverPick({
        canvasRef,
        dragRef,
        nodeDragRef,
        getPositionsForFrame,
        graph: { nodes: [], edges: [] },
        transformRef,
        resolveNodeCanvasLabel: () => null,
        graphColorBy: "type",
        searchActive: false,
        searchMatchSet: null,
        selectedNodeId: "",
        canvasLabelMode: "adaptive",
        activeForLabelSetRef: null,
      }),
    );

    act(() => {
      result.current.queueHoverPick(1, 2);
    });
    unmount();
    expect(cancelSpy).toHaveBeenCalledWith(4242);
  });
});
