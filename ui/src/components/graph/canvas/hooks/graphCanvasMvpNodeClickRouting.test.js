/** @vitest-environment jsdom */
import { describe, expect, it, vi } from "vitest";

import { routeGraphCanvasNodeClick } from "./graphCanvasMvpNodeClickRouting.js";

describe("routeGraphCanvasNodeClick", () => {
  it("calls onAggregatorExpand when Aggregator has expand_endpoint", () => {
    const onAggregatorExpand = vi.fn();
    const onSelectNode = vi.fn();
    const agg = {
      id: "g1",
      nodeKind: "Aggregator",
      raw: { aggregation_hints: { expand_endpoint: "https://example.com/expand" } },
    };
    const nodeById = new Map([["g1", agg]]);
    routeGraphCanvasNodeClick({ nodeById, nodeId: "g1", onAggregatorExpand, onSelectNode });
    expect(onAggregatorExpand).toHaveBeenCalledWith(agg, "https://example.com/expand");
    expect(onSelectNode).not.toHaveBeenCalled();
  });

  it("falls through to onSelectNode for non-aggregator nodes", () => {
    const onAggregatorExpand = vi.fn();
    const onSelectNode = vi.fn();
    const node = { id: "n1", nodeKind: "Work" };
    const nodeById = new Map([["n1", node]]);
    routeGraphCanvasNodeClick({ nodeById, nodeId: "n1", onAggregatorExpand, onSelectNode });
    expect(onAggregatorExpand).not.toHaveBeenCalled();
    expect(onSelectNode).toHaveBeenCalledWith("n1");
  });

  it("falls through to onSelectNode when Aggregator has no expand_endpoint", () => {
    const onAggregatorExpand = vi.fn();
    const onSelectNode = vi.fn();
    const agg = { id: "g1", nodeKind: "Aggregator", raw: {} };
    const nodeById = new Map([["g1", agg]]);
    routeGraphCanvasNodeClick({ nodeById, nodeId: "g1", onAggregatorExpand, onSelectNode });
    expect(onAggregatorExpand).not.toHaveBeenCalled();
    expect(onSelectNode).toHaveBeenCalledWith("g1");
  });
});
