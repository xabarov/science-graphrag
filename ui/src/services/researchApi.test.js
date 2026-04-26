import { describe, expect, it } from "vitest";

import { SAMPLE_QUERY_SEMANTIC_OFF, SAMPLE_QUERY_SEMANTIC_ON } from "../fixtures/researchSemanticSamples.js";
import {
  buildAskAnswerRationale,
  buildQueryBody,
  formatResearchApiError,
  formatRetrievalSummaryLines,
  normalizeQueryResponse,
} from "./researchApi.js";

describe("formatResearchApiError", () => {
  it("prefers FastAPI string detail from axios-like error", () => {
    expect(
      formatResearchApiError({
        response: { data: { detail: "not_found" } },
      }),
    ).toBe("not_found");
  });

  it("stringifies object detail", () => {
    expect(
      formatResearchApiError({
        response: { data: { detail: [{ loc: ["body"], msg: "x", type: "y" }] } },
      }),
    ).toBe(JSON.stringify([{ loc: ["body"], msg: "x", type: "y" }]));
  });

  it("falls back to Error message", () => {
    expect(formatResearchApiError(new Error("network"))).toBe("network");
  });

  it("stringifies unknown values", () => {
    expect(formatResearchApiError(null)).toBe("null");
  });
});

describe("buildQueryBody", () => {
  it("trims query and maps empty work id to null", () => {
    expect(buildQueryBody("  q  ", "", 3)).toEqual({
      query: "q",
      work_id: null,
      workspace_id: null,
      top_k: 3,
      mode: "vector",
    });
  });

  it("clamps top_k to [1, 24]", () => {
    expect(buildQueryBody("x", null, 0).top_k).toBe(1);
    expect(buildQueryBody("x", null, 999).top_k).toBe(24);
  });
});

describe("formatRetrievalSummaryLines", () => {
  it("returns metric lines for a trace object", () => {
    const lines = formatRetrievalSummaryLines({
      hit_count: 3,
      citations_returned: 2,
      top_k_requested: 5,
      qdrant_collection: "chunks",
      retrieval_policy: "semantic",
      filter_work_id: null,
      resolved_work_id: "w1",
      degraded: ["x"],
    });
    expect(lines.some((l) => l.includes("Hits: 3"))).toBe(true);
    expect(lines.some((l) => l.includes("chunks"))).toBe(true);
    expect(lines.some((l) => l.includes("Degraded"))).toBe(true);
  });
});

describe("buildAskAnswerRationale", () => {
  const base = normalizeQueryResponse({
    answer: "a",
    citations: [{ rank: 1 }],
    graph_context: { semantic_available: true, methods: [], datasets: [], degraded: [], error: null, context_work_id: null },
    retrieval_trace: {
      hit_count: 4,
      top_k_requested: 5,
      citations_returned: 1,
      degraded: [],
    },
  });

  it("uses workspace wording when locked", () => {
    const b = buildAskAnswerRationale(base, { locked: true, inWorkspace: true, formWorkId: "w" });
    expect(b[0]).toMatch(/workspace session/i);
  });

  it("uses corpus-wide wording when no work id and not workspace", () => {
    const b = buildAskAnswerRationale(base, { locked: false, inWorkspace: false, formWorkId: "" });
    expect(b[0]).toMatch(/corpus-wide/i);
  });

  it("uses paper-scoped wording when form work id set outside workspace", () => {
    const b = buildAskAnswerRationale(base, { locked: false, inWorkspace: false, formWorkId: "paper-1" });
    expect(b[0]).toMatch(/paper-scoped/i);
  });

  it("mentions degraded when flags present", () => {
    const n = normalizeQueryResponse({
      answer: "a",
      citations: [],
      graph_context: { semantic_available: false, methods: [], datasets: [], degraded: ["x"], error: null, context_work_id: null },
      retrieval_trace: { hit_count: 0, top_k_requested: 3, citations_returned: 0, degraded: ["y"] },
    });
    const b = buildAskAnswerRationale(n, { locked: false, inWorkspace: false, formWorkId: "" });
    expect(b.some((line) => /degraded/i.test(line))).toBe(true);
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

describe("normalizeQueryResponse (agent v2 envelope)", () => {
  it("passes through optional chat fields", () => {
    const n = normalizeQueryResponse({
      answer: "x",
      citations: [],
      graph_context: {},
      retrieval_trace: {},
      answer_class: "inventory",
      evidence_summary: "3 citation(s)",
      warnings: ["no_workspace", "some_work_ids_filtered"],
      inventory: { work_count: 2 },
      quote_candidates: [{ quote_text: "hi", work_id: "w1" }],
      bibliography: { format: "gost", entries: ["A. B. Title"], filtered_work_ids: ["z"] },
      thread_id: "sess-1",
    });
    expect(n.answer_class).toBe("inventory");
    expect(n.evidence_summary).toBe("3 citation(s)");
    expect(n.warnings).toEqual(["no_workspace", "some_work_ids_filtered"]);
    expect(n.inventory?.work_count).toBe(2);
    expect(n.quote_candidates?.length).toBe(1);
    expect(n.bibliography?.format).toBe("gost");
    expect(n.thread_id).toBe("sess-1");
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
