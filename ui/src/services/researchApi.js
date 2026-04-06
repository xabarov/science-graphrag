import axios from "axios";

/**
 * Base URL for the research API (no trailing slash). Empty string = same-origin `/v1/*`
 * (Vite dev proxy + FastAPI static deploy).
 */
export function getResearchApiBaseUrl() {
  const v = import.meta.env.VITE_API_BASE_URL;
  if (v == null || String(v).trim() === "") return "";
  return String(v).replace(/\/+$/, "");
}

export function buildQueryBody(query, workId = null, topK = 5) {
  const t = Math.trunc(Number(topK));
  const tk = Number.isFinite(t) ? Math.min(24, Math.max(1, t)) : 5;
  const wid = workId === undefined || workId === "" ? null : workId;
  return {
    query: String(query ?? "").trim(),
    work_id: wid,
    top_k: tk,
  };
}

const EMPTY_GRAPH_CONTEXT = {
  methods: [],
  datasets: [],
  semantic_available: false,
  context_work_id: null,
  degraded: [],
  error: null,
};

const EMPTY_RETRIEVAL_TRACE = {
  embedding: {},
  hit_count: 0,
  filter_work_id: null,
  resolved_work_id: null,
  qdrant_collection: "",
  top_k_requested: 0,
  citations_returned: 0,
  degraded: [],
};

/** Normalize `/v1/query` JSON for UI rendering (pure). */
export function normalizeQueryResponse(raw) {
  if (raw == null || typeof raw !== "object") {
    return {
      answer: "",
      citations: [],
      graph_context: { ...EMPTY_GRAPH_CONTEXT },
      retrieval_trace: { ...EMPTY_RETRIEVAL_TRACE },
    };
  }
  const gc = raw.graph_context && typeof raw.graph_context === "object" ? raw.graph_context : {};
  const rt = raw.retrieval_trace && typeof raw.retrieval_trace === "object" ? raw.retrieval_trace : {};
  return {
    answer: typeof raw.answer === "string" ? raw.answer : "",
    citations: Array.isArray(raw.citations) ? raw.citations : [],
    graph_context: {
      methods: Array.isArray(gc.methods) ? gc.methods : [],
      datasets: Array.isArray(gc.datasets) ? gc.datasets : [],
      semantic_available: Boolean(gc.semantic_available),
      context_work_id: gc.context_work_id == null ? null : String(gc.context_work_id),
      degraded: Array.isArray(gc.degraded) ? gc.degraded.map(String) : [],
      error: gc.error == null ? null : String(gc.error),
    },
    retrieval_trace: {
      embedding: rt.embedding && typeof rt.embedding === "object" ? rt.embedding : {},
      hit_count: Number.isFinite(Number(rt.hit_count)) ? Number(rt.hit_count) : 0,
      filter_work_id: rt.filter_work_id == null ? null : String(rt.filter_work_id),
      resolved_work_id: rt.resolved_work_id == null ? null : String(rt.resolved_work_id),
      qdrant_collection: rt.qdrant_collection == null ? "" : String(rt.qdrant_collection),
      top_k_requested: Number.isFinite(Number(rt.top_k_requested)) ? Number(rt.top_k_requested) : 0,
      citations_returned: Number.isFinite(Number(rt.citations_returned)) ? Number(rt.citations_returned) : 0,
      degraded: Array.isArray(rt.degraded) ? rt.degraded.map(String) : [],
    },
  };
}

export async function postQuery(body, config) {
  const base = getResearchApiBaseUrl();
  const path = "/v1/query";
  const url = base ? `${base}${path}` : path;
  return axios.post(url, body, config);
}

function worksUrl(pathWithQuery) {
  const base = getResearchApiBaseUrl();
  return base ? `${base}${pathWithQuery}` : pathWithQuery;
}

/** GET /v1/works */
export async function getWorks({ q, limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (q != null && String(q).trim() !== "") params.set("q", String(q).trim());
  return axios.get(worksUrl(`/v1/works?${params.toString()}`));
}

/** GET /v1/works/{work_id} */
export async function getWorkDetail(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return axios.get(worksUrl(`/v1/works/${id}`));
}

/** GET /v1/works/{work_id}/chunks */
export async function getWorkChunks(workId, { limit = 50, offset = 0, section_prefix: sectionPrefix } = {}) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (sectionPrefix != null && String(sectionPrefix).trim() !== "") {
    params.set("section_prefix", String(sectionPrefix).trim());
  }
  return axios.get(worksUrl(`/v1/works/${id}/chunks?${params.toString()}`));
}

/** GET /v1/works/{work_id}/graph */
export async function getWorkGraph(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return axios.get(worksUrl(`/v1/works/${id}/graph`));
}
