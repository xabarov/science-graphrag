import { describe, expect, it } from "vitest";

import { deriveInspectorDetail } from "./graphInspectorModel.js";
import { normalizeGraphPayload } from "./graphViewState.js";
import {
  capGraphForUi,
  GRAPH_CAP_WARNING_LARGE_PAYLOAD,
  WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT,
  WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT,
} from "./graphUiLimits.js";

describe("graphUiLimits", () => {
  it("returns empty graph shape when input is null without warnings", () => {
    const { displayGraph, capWarnings } = capGraphForUi(null);
    expect(displayGraph.nodes).toEqual([]);
    expect(displayGraph.edges).toEqual([]);
    expect(capWarnings).toHaveLength(0);
  });

  it("returns same graph reference and no warnings", () => {
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

  it("does not truncate large node sets", () => {
    const nodes = Array.from({ length: 500 }, (_, i) => ({ id: `n${i}` }));
    const graph = { nodes, edges: [] };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.nodes).toHaveLength(500);
    expect(capWarnings).toHaveLength(0);
  });

  it("does not truncate large edge sets", () => {
    const nodes = Array.from({ length: 5 }, (_, i) => ({ id: `n${i}` }));
    const edges = Array.from({ length: 700 }, (_, i) => ({
      source: "n0",
      target: `n${1 + (i % 4)}`,
    }));
    const graph = { nodes, edges };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.edges).toHaveLength(700);
    expect(capWarnings).toHaveLength(0);
  });

  it("adds performance warning at node warn threshold without truncating", () => {
    const nodes = Array.from({ length: WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT }, (_, i) => ({ id: `n${i}` }));
    const graph = { nodes, edges: [] };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.nodes).toHaveLength(WORKSPACE_GRAPH_PERF_WARN_NODE_COUNT);
    expect(capWarnings).toContain(GRAPH_CAP_WARNING_LARGE_PAYLOAD);
  });

  it("adds performance warning at edge warn threshold without truncating", () => {
    const nodes = [{ id: "a" }, { id: "b" }];
    const edges = Array.from({ length: WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT }, (_, i) => ({
      id: `e${i}`,
      source: "a",
      target: "b",
    }));
    const graph = { nodes, edges };
    const { displayGraph, capWarnings } = capGraphForUi(graph);
    expect(displayGraph.edges).toHaveLength(WORKSPACE_GRAPH_PERF_WARN_EDGE_COUNT);
    expect(capWarnings).toContain(GRAPH_CAP_WARNING_LARGE_PAYLOAD);
  });

  it("keeps connected author-work pair in full graph", () => {
    const filler = Array.from({ length: 200 }, (_, i) => ({ id: `n${i}`, type: "Work" }));
    const graph = {
      nodes: [...filler, { id: "a1", type: "Author" }, { id: "w1", type: "Work" }],
      edges: [{ id: "e1", source: "w1", target: "a1", type: "AUTHORED" }],
    };
    const { displayGraph } = capGraphForUi(graph, "");
    expect(displayGraph.nodes.some((n) => n.id === "a1")).toBe(true);
    expect(displayGraph.nodes.some((n) => n.id === "w1")).toBe(true);
    expect(displayGraph.edges).toHaveLength(1);
  });

  it("keeps preferred connected node and its neighborhood when explicitly selected", () => {
    const filler = Array.from({ length: 200 }, (_, i) => ({ id: `n${i}`, type: "Work" }));
    const graph = {
      nodes: [...filler, { id: "a1", type: "Author" }, { id: "w1", type: "Work" }],
      edges: [{ id: "e1", source: "w1", target: "a1", type: "AUTHORED" }],
    };
    const { displayGraph } = capGraphForUi(graph, "a1");
    expect(displayGraph.nodes.some((n) => n.id === "a1")).toBe(true);
    expect(displayGraph.nodes.some((n) => n.id === "w1")).toBe(true);
    expect(displayGraph.edges).toHaveLength(1);
  });

  it("inspector author rows still need the underlying full graph shape", () => {
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
});
