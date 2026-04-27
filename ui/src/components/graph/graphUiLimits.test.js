import { describe, expect, it } from "vitest";

import { deriveInspectorDetail } from "./graphInspectorModel.js";
import { normalizeGraphPayload } from "./graphViewState.js";
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

  it("inspector author rows need full graph: cap can drop Work and AUTHORED edges", () => {
    const full = normalizeGraphPayload({
      nodes: [
        { id: "w1", type: "Work", label: "Paper", node_kind: "Work" },
        { id: "a1", type: "Author", label: "Ann", node_kind: "Author" },
      ],
      edges: [{ id: "e1", source: "w1", target: "a1", type: "AUTHORED", properties: { author_position: 1 } }],
      meta: {},
    });
    expect(deriveInspectorDetail(full, "a1", "").authorAuthoredWorks).toHaveLength(1);
    const { displayGraph } = capGraphForUi({ ...full, nodes: [full.nodes[1]], edges: [] }, "a1");
    expect(deriveInspectorDetail(displayGraph, "a1", "").authorAuthoredWorks).toHaveLength(0);
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
