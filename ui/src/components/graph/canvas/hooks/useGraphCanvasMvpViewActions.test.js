/** @vitest-environment jsdom */
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildSimulationState } from "../../model/graphSimulationAdapter.js";
import { useGraphCanvasMvpViewActions } from "./useGraphCanvasMvpViewActions.js";

vi.mock("../../model/graphSimulationAdapter.js", () => ({
  buildSimulationState: vi.fn(),
}));

describe("useGraphCanvasMvpViewActions", () => {
  beforeEach(() => {
    vi.mocked(buildSimulationState).mockReturnValue({
      nodes: [
        { id: "a", x: 10, y: 20 },
        { id: "b", x: 30, y: 40 },
      ],
      links: [{ id: "l1", source: "a", target: "b", type: "X" }],
    });
  });

  it("handleRestart in force mode clears pins, rebuilds sim, bumps nonce, applyFit with seed", () => {
    const applyFit = vi.fn();
    const setSimNodes = vi.fn();
    const setSimLinks = vi.fn();
    const setForceSimRunNonce = vi.fn();
    const setPhysicsReheatNonce = vi.fn();
    const setIsSimulationStable = vi.fn();
    const setPinnedNodeCount = vi.fn();
    const fixedNodesRef = { current: new Set(["a"]) };
    const draggedNodePositionRef = { current: { id: "a", x: 0, y: 0 } };
    const simNodesRef = { current: [] };
    const positionsRef = { current: new Map() };

    const { result } = renderHook(() =>
      useGraphCanvasMvpViewActions({
        layoutMode: "force",
        graph: {
          nodes: [
            { id: "a", type: "Work", label: "A" },
            { id: "b", type: "Method", label: "B" },
          ],
          edges: [],
        },
        applyFit,
        getPositionsForFrame: () => new Map(),
        getViewportDims: () => ({ w: 400, h: 300 }),
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        setTransform: vi.fn(),
        selectedNodeId: "",
        centerViewportOnNode: vi.fn(),
        setCanvasLabelMode: vi.fn(),
        setHoverNeighborsLabels: vi.fn(),
        fixedNodesRef,
        draggedNodePositionRef,
        setPinnedNodeCount,
        setSimNodes,
        setSimLinks,
        simNodesRef,
        positionsRef,
        setForceSimRunNonce,
        setPhysicsReheatNonce,
        setIsSimulationStable,
        canvasLabelMode: "adaptive",
      }),
    );

    act(() => {
      result.current.handleRestart();
    });

    expect(fixedNodesRef.current.size).toBe(0);
    expect(draggedNodePositionRef.current).toBeNull();
    expect(setPinnedNodeCount).toHaveBeenCalledWith(0);
    expect(buildSimulationState).toHaveBeenCalled();
    expect(setSimLinks).toHaveBeenCalled();
    expect(setSimNodes).toHaveBeenCalled();
    expect(setForceSimRunNonce).toHaveBeenCalled();
    expect(setIsSimulationStable).toHaveBeenCalledWith(false);
    expect(applyFit).toHaveBeenCalledWith(
      "force",
      expect.objectContaining({
        size: 2,
        get: expect.any(Function),
      }),
    );
  });

  it("handleRestart is no-op when layoutMode is not force", () => {
    const applyFit = vi.fn();
    const fixedNodesRef = { current: new Set(["a"]) };

    const { result } = renderHook(() =>
      useGraphCanvasMvpViewActions({
        layoutMode: "circle",
        graph: { nodes: [{ id: "a" }], edges: [] },
        applyFit,
        getPositionsForFrame: () => new Map(),
        getViewportDims: () => ({ w: 400, h: 300 }),
        transformRef: { current: { scale: 1, tx: 0, ty: 0 } },
        setTransform: vi.fn(),
        selectedNodeId: "",
        centerViewportOnNode: vi.fn(),
        setCanvasLabelMode: vi.fn(),
        setHoverNeighborsLabels: vi.fn(),
        fixedNodesRef,
        draggedNodePositionRef: { current: null },
        setPinnedNodeCount: vi.fn(),
        setSimNodes: vi.fn(),
        setSimLinks: vi.fn(),
        simNodesRef: { current: [] },
        positionsRef: { current: new Map() },
        setForceSimRunNonce: vi.fn(),
        setPhysicsReheatNonce: vi.fn(),
        setIsSimulationStable: vi.fn(),
        canvasLabelMode: "adaptive",
      }),
    );

    act(() => {
      result.current.handleRestart();
    });

    expect(applyFit).not.toHaveBeenCalled();
    expect(fixedNodesRef.current.has("a")).toBe(true);
  });
});
