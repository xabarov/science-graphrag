import { describe, expect, it } from "vitest";

import { capGraphForUi, GRAPH_UI_MAX_EDGES, GRAPH_UI_MAX_NODES } from "./graphUiLimits.js";

describe("graphUiLimits", () => {
  it("returns same graph reference when under caps (stable for selection re-renders)", () => {
    const graph = {
      nodes: [{ id: "a" }, { id: "b" }],
      edges: [{ source: "a", target: "b" }],
    };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(capWarnings).toHaveLength(0);
    expect(displayGraph).toBe(graph);
    expect(displayGraph.nodes).toHaveLength(2);
    expect(displayGraph.edges).toHaveLength(1);
  });

  it("truncates nodes and warns", () => {
    const nodes = Array.from({ length: GRAPH_UI_MAX_NODES + 10 }, (_, i) => ({ id: `n${i}` }));
    const graph = { nodes, edges: [] };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.nodes).toHaveLength(GRAPH_UI_MAX_NODES);
    expect(capWarnings.some((w) => w.includes("Performance cap"))).toBe(true);
  });

  it("truncates edges after node cap and warns on edge cap", () => {
    const nodes = Array.from({ length: 5 }, (_, i) => ({ id: `n${i}` }));
    const edges = Array.from({ length: GRAPH_UI_MAX_EDGES + 5 }, (_, i) => ({
      source: "n0",
      target: `n${1 + (i % 4)}`,
    }));
    const graph = { nodes, edges };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.edges.length).toBeLessThanOrEqual(GRAPH_UI_MAX_EDGES);
    expect(capWarnings.length).toBeGreaterThanOrEqual(1);
  });

  it("keeps preferred node id inside the node cap when possible", () => {
    const nodes = Array.from({ length: GRAPH_UI_MAX_NODES + 3 }, (_, i) => ({ id: `n${i}` }));
    const graph = { nodes, edges: [] };
    const preferred = `n${GRAPH_UI_MAX_NODES + 1}`;
    const { displayGraph, capWarnings } = capGraphForUi(graph, preferred);
    expect(capWarnings.length).toBeGreaterThan(0);
    expect(displayGraph.nodes.some((n) => n.id === preferred)).toBe(true);
  });
});
