/** @vitest-environment jsdom */
import React from "react";
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GraphPhysicsPointerBridgeProvider } from "../GraphPhysicsPointerBridgeContext.jsx";
import { useGraphCanvasMvpController } from "./useGraphCanvasMvpController.js";

function wrapper({ children }) {
  return <GraphPhysicsPointerBridgeProvider>{children}</GraphPhysicsPointerBridgeProvider>;
}

const minimalGraph = {
  nodes: [{ id: "n1", type: "Work", label: "N1" }],
  edges: [],
};

const baseProps = {
  graph: minimalGraph,
  selectedNodeId: "",
  selectedEdgeId: "",
  onSelectNode: vi.fn(),
  onSelectEdge: vi.fn(),
  layoutMode: "circle",
  onCanvasLayoutModeChange: vi.fn(),
  onAggregatorExpand: vi.fn(),
  searchMatchIds: null,
  searchQuery: "",
  centerRequestNonce: 0,
  centerRequestNodeId: "",
  graphColorBy: "type",
  graphCommunityHulls: false,
  nodeCommunityMap: new Map(),
  t: (k) => k,
  appearance: "dark",
  canvasBg: "#000000",
};

describe("useGraphCanvasMvpController", () => {
  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", (cb) => {
      queueMicrotask(() => cb(0));
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  it("mounts and exposes core surface", () => {
    const { result } = renderHook(() => useGraphCanvasMvpController(baseProps), { wrapper });
    expect(result.current.applyFit).toBeInstanceOf(Function);
    expect(result.current.handleRestart).toBeInstanceOf(Function);
    expect(result.current.handleCanvasContextMenu).toBeInstanceOf(Function);
    expect(result.current.input).toBeDefined();
    expect(result.current.edgeLegendTypes).toEqual([]);
  });
});
