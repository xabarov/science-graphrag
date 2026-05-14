/** @vitest-environment jsdom */

import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useGraphFlowSelectionHandlers } from "./hooks/useGraphFlowSelectionHandlers.js";

describe("useGraphFlowSelectionHandlers", () => {
  it("handleCenterSelection does not throw when graph.edges is missing", () => {
    const fitView = vi.fn();
    const zoomTo = vi.fn();
    const graph = { nodes: [] };
    const { result } = renderHook(() =>
      useGraphFlowSelectionHandlers({
        graph,
        selectedNodeId: "",
        selectedEdgeId: "e1",
        onSelectNode: vi.fn(),
        onSelectEdge: vi.fn(),
        fitView,
        zoomTo,
      }),
    );
    expect(() => result.current.handleCenterSelection()).not.toThrow();
  });

  it("exposes canCenter when node or edge selected", () => {
    const fitView = vi.fn();
    const zoomTo = vi.fn();
    const graph = { edges: [{ id: "e1", source: "a", target: "b" }] };
    const { result, rerender } = renderHook(
      (props) =>
        useGraphFlowSelectionHandlers({
          graph,
          selectedNodeId: props.selectedNodeId,
          selectedEdgeId: props.selectedEdgeId,
          onSelectNode: vi.fn(),
          onSelectEdge: vi.fn(),
          fitView,
          zoomTo,
        }),
      { initialProps: { selectedNodeId: "", selectedEdgeId: "" } },
    );
    expect(result.current.canCenter).toBe(false);
    rerender({ selectedNodeId: "n1", selectedEdgeId: "" });
    expect(result.current.canCenter).toBe(true);
    rerender({ selectedNodeId: "", selectedEdgeId: "e1" });
    expect(result.current.canCenter).toBe(true);
  });
});
