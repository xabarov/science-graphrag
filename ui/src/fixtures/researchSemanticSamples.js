/**
 * Sample `/v1/query` payloads for UI/tests — semantic layer present vs missing.
 * Phase 6 bridge backlog A3: deterministic states without live Neo4j/Qdrant.
 */

export const SAMPLE_QUERY_SEMANTIC_ON = {
  answer: "Methods include YOLO and SSD.",
  citations: [
    {
      rank: 1,
      score: 0.42,
      work_id: "w-demo",
      document_id: "d-demo",
      chunk_fingerprint: "fp-demo-1",
      section_path: "3 Methods",
      excerpt: "We use a single-stage detector…",
    },
  ],
  graph_context: {
    methods: ["YOLO", "SSD"],
    datasets: ["COCO"],
    semantic_available: true,
    context_work_id: "w-demo",
    degraded: [],
    error: null,
  },
  retrieval_trace: {
    embedding: { embedding_model: "demo", vector_dim: 8 },
    hit_count: 3,
    filter_work_id: null,
    resolved_work_id: "w-demo",
    qdrant_collection: "chunks",
    top_k_requested: 5,
    citations_returned: 1,
    degraded: [],
  },
};

export const SAMPLE_QUERY_SEMANTIC_OFF = {
  answer: "Backbone-only: no semantic extraction for this work.",
  citations: [],
  graph_context: {
    methods: [],
    datasets: [],
    semantic_available: false,
    context_work_id: null,
    degraded: ["semantic_layer_disabled"],
    error: null,
  },
  retrieval_trace: {
    embedding: {},
    hit_count: 0,
    filter_work_id: null,
    resolved_work_id: null,
    qdrant_collection: "",
    top_k_requested: 5,
    citations_returned: 0,
    degraded: ["no_retrieval_hits"],
  },
};
