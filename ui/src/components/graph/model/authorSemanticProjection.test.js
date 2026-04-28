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

  it("projectAuthorSemanticGraph is pass-through for server-normalized reader graph", () => {
    const g = normalizeGraphPayload({
      nodes: [
        { id: "w1", type: "Work", label: "SSD", nodeKind: "Work" },
        { id: "a1", type: "Author", label: "Alice", nodeKind: "Author" },
      ],
      edges: [
        {
          id: "e1",
          source: "w1",
          target: "a1",
          type: "AUTHORED",
          raw: { type: "AUTHORED" },
        },
      ],
      meta: {},
    });
    const p = projectAuthorSemanticGraph(g);
    expect(p).toBe(g);
    expect(p.nodes).toHaveLength(2);
    expect(p.edges.filter((e) => String(e.type).toUpperCase() === "AUTHORED")).toHaveLength(1);
  });
});
