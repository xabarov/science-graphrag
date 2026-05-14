/** @vitest-environment jsdom */

import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useGraphWorkspacePanelActions } from "./useGraphWorkspacePanelActions.js";

describe("useGraphWorkspacePanelActions", () => {
  it("focusFirstLocalMatch tolerates missing displayGraph.nodes", () => {
    const setDetailsVisible = vi.fn();
    const onSelectNode = vi.fn();
    const setCenterCanvasNodeId = vi.fn();
    const setCenterCanvasNonce = vi.fn();
    const displayGraph = {};
    const nodeSearchMatchIds = new Set(["a"]);
    const { result } = renderHook(() =>
      useGraphWorkspacePanelActions({
        detailsVisible: true,
        setDetailsVisible,
        onSelectNode,
        onSelectEdge: vi.fn(),
        displayGraph,
        nodeSearchMatchIds,
        setGraphColorBy: vi.fn(),
        setGraphCommunityHulls: vi.fn(),
        setCenterCanvasNodeId,
        setCenterCanvasNonce,
      }),
    );
    expect(() => result.current.focusFirstLocalMatch()).not.toThrow();
    expect(onSelectNode).not.toHaveBeenCalled();
  });
});
