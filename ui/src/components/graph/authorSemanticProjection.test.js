import { describe, expect, it } from "vitest";

import {
  collectAuthorAggregatorExpandEndpoints,
  projectAuthorSemanticGraph,
} from "./authorSemanticProjection.js";
import { normalizeGraphPayload } from "./graphViewState.js";

describe("authorSemanticProjection", () => {
  it("collectAuthorAggregatorExpandEndpoints returns unique expand URLs for author aggregators", () => {
    const g = normalizeGraphPayload({
      nodes: [
        {
          id: "agg1",
          type: "Aggregator",
          node_kind: "Aggregator",
          aggregation_hints: {
            aggregator_kind: "author_of_work",
            count: 3,
            expand_endpoint: "/v1/workspaces/ws/graph/expand?aggregator_id=agg1",
          },
        },
        {
          id: "agg2",
          type: "Aggregator",
          node_kind: "Aggregator",
          aggregation_hints: {
            aggregator_kind: "method_of_work",
            count: 5,
            expand_endpoint: "/v1/workspaces/ws/graph/expand?aggregator_id=agg2",
          },
        },
      ],
      edges: [],
      meta: {},
    });
    const eps = collectAuthorAggregatorExpandEndpoints(g);
    expect(eps).toEqual(["/v1/workspaces/ws/graph/expand?aggregator_id=agg1"]);
  });

  it("removes author aggregator and authorship chain, adds AUTHORED edge", () => {
    const g = normalizeGraphPayload({
      nodes: [
        { id: "w1", type: "Work", label: "SSD", node_kind: "Work" },
        { id: "ash1", type: "Authorship", label: "Alice (#1)", node_kind: "Authorship", properties: { author_position: 1 } },
        { id: "a1", type: "Author", label: "Alice", node_kind: "Author" },
        {
          id: "agg:1",
          type: "Aggregator",
          node_kind: "Aggregator",
          aggregation_hints: {
            aggregator_kind: "author_of_work",
            count: 1,
            expand_endpoint: "/x",
          },
        },
      ],
      edges: [
        { id: "e1", source: "w1", target: "ash1", type: "HAS_AUTHORSHIP" },
        { id: "e2", source: "ash1", target: "a1", type: "OF_AUTHOR" },
        { id: "e3", source: "w1", target: "agg:1", type: "AGGREGATED" },
      ],
      meta: {},
    });
    const p = projectAuthorSemanticGraph(g);
    expect(p.nodes.map((n) => n.id).sort()).toEqual(["a1", "w1"]);
    const authored = p.edges.filter((e) => String(e.type).toUpperCase() === "AUTHORED");
    expect(authored).toHaveLength(1);
    expect(authored[0].source).toBe("w1");
    expect(authored[0].target).toBe("a1");
    expect(authored[0].raw?.properties?.author_position).toBe(1);
  });

  it("synthesizes Author nodes from Authorship when explicit Author nodes are absent", () => {
    const g = normalizeGraphPayload({
      nodes: [
        { id: "w1", type: "Work", label: "SSD", node_kind: "Work" },
        {
          id: "ash1",
          type: "Authorship",
          label: "Alice (#1)",
          display_label: "Alice (#1)",
          subtitle: "Author #1 · IBM Research",
          node_kind: "Authorship",
          properties: { author_position: 1 },
        },
      ],
      edges: [{ id: "e1", source: "w1", target: "ash1", type: "HAS_AUTHORSHIP" }],
      meta: {},
    });
    const p = projectAuthorSemanticGraph(g);
    expect(p.nodes.map((n) => ({ id: n.id, type: n.type, label: n.displayLabel }))).toEqual([
      { id: "w1", type: "Work", label: "SSD" },
      { id: "ash1", type: "Author", label: "Alice" },
    ]);
    const authored = p.edges.filter((e) => String(e.type).toUpperCase() === "AUTHORED");
    expect(authored).toHaveLength(1);
    expect(authored[0].source).toBe("w1");
    expect(authored[0].target).toBe("ash1");
  });

  it("bridges Authorship AFFILIATED_WITH to Author–Institution", () => {
    const g = normalizeGraphPayload({
      nodes: [
        { id: "w1", type: "Work", label: "Paper", node_kind: "Work" },
        { id: "ash1", type: "Authorship", label: "Bob (#2)", node_kind: "Authorship" },
        { id: "a1", type: "Author", label: "Bob", node_kind: "Author" },
        { id: "i1", type: "Institution", label: "MIT", node_kind: "Institution" },
      ],
      edges: [
        { id: "e1", source: "w1", target: "ash1", type: "HAS_AUTHORSHIP" },
        { id: "e2", source: "ash1", target: "a1", type: "OF_AUTHOR" },
        { id: "e3", source: "ash1", target: "i1", type: "AFFILIATED_WITH" },
      ],
      meta: {},
    });
    const p = projectAuthorSemanticGraph(g);
    const aff = p.edges.filter((e) => String(e.type).toUpperCase() === "AFFILIATED_WITH");
    expect(aff.some((e) => e.source === "a1" && e.target === "i1")).toBe(true);
  });
});
