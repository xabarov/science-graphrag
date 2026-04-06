import { describe, expect, it } from "vitest";

import { SAMPLE_QUERY_SEMANTIC_OFF, SAMPLE_QUERY_SEMANTIC_ON } from "../fixtures/researchSemanticSamples.js";
import { buildQueryBody, normalizeQueryResponse } from "./researchApi.js";

describe("buildQueryBody", () => {
  it("trims query and maps empty work id to null", () => {
    expect(buildQueryBody("  q  ", "", 3)).toEqual({
      query: "q",
      work_id: null,
      top_k: 3,
    });
  });

  it("clamps top_k to [1, 24]", () => {
    expect(buildQueryBody("x", null, 0).top_k).toBe(1);
    expect(buildQueryBody("x", null, 999).top_k).toBe(24);
  });
});

describe("normalizeQueryResponse", () => {
  it("fills defaults for null", () => {
    const n = normalizeQueryResponse(null);
    expect(n.answer).toBe("");
    expect(n.citations).toEqual([]);
    expect(n.graph_context.semantic_available).toBe(false);
    expect(n.graph_context.degraded).toEqual([]);
    expect(n.retrieval_trace.qdrant_collection).toBe("");
    expect(n.retrieval_trace.degraded).toEqual([]);
  });

  it("preserves degraded flags and trace fields", () => {
    const n = normalizeQueryResponse({
      answer: "a",
      citations: [{ rank: 1 }],
      graph_context: {
        methods: ["m"],
        datasets: [],
        semantic_available: true,
        context_work_id: "w1",
        degraded: ["no_resolved_work"],
        error: null,
      },
      retrieval_trace: {
        embedding: { embedding_model: "e5" },
        hit_count: 2,
        filter_work_id: null,
        resolved_work_id: "w1",
        qdrant_collection: "chunks",
        top_k_requested: 5,
        citations_returned: 1,
        degraded: ["no_retrieval_hits"],
      },
    });
    expect(n.graph_context.degraded).toEqual(["no_resolved_work"]);
    expect(n.retrieval_trace.qdrant_collection).toBe("chunks");
    expect(n.retrieval_trace.degraded).toEqual(["no_retrieval_hits"]);
  });
});

describe("fixture packs (semantic on/off)", () => {
  it("normalizes semantic-on sample", () => {
    const n = normalizeQueryResponse(SAMPLE_QUERY_SEMANTIC_ON);
    expect(n.graph_context.semantic_available).toBe(true);
    expect(n.graph_context.methods.length).toBeGreaterThan(0);
    expect(n.citations[0].chunk_fingerprint).toBe("fp-demo-1");
  });

  it("normalizes semantic-off sample", () => {
    const n = normalizeQueryResponse(SAMPLE_QUERY_SEMANTIC_OFF);
    expect(n.graph_context.semantic_available).toBe(false);
    expect(n.graph_context.degraded).toContain("semantic_layer_disabled");
    expect(n.citations.length).toBe(0);
  });
});
