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
  retrieval_policy: null,
  filter_work_id: null,
  resolved_work_id: null,
  qdrant_collection: "",
  top_k_requested: 0,
  citations_returned: 0,
  degraded: [],
};

/** Human-readable retrieval metrics for Ask UI (pure). */
export function formatRetrievalSummaryLines(rt) {
  if (!rt || typeof rt !== "object") return [];
  const lines = [];
  lines.push(`Hits: ${Number(rt.hit_count) || 0} · Citations returned: ${Number(rt.citations_returned) || 0}`);
  lines.push(`top_k requested: ${Number(rt.top_k_requested) || 0}`);
  const coll = rt.qdrant_collection != null && String(rt.qdrant_collection).trim() !== "" ? String(rt.qdrant_collection) : "—";
  lines.push(`Collection: ${coll}`);
  const policy = rt.retrieval_policy != null ? String(rt.retrieval_policy) : "—";
  lines.push(`Retrieval policy: ${policy}`);
  const fw = rt.filter_work_id != null ? String(rt.filter_work_id) : "none";
  const rw = rt.resolved_work_id != null ? String(rt.resolved_work_id) : "—";
  lines.push(`Filter work_id: ${fw} · Resolved work_id: ${rw}`);
  if (Array.isArray(rt.degraded) && rt.degraded.length > 0) {
    lines.push(`Degraded steps: ${rt.degraded.length}`);
  }
  return lines;
}

/**
 * Short product-facing bullets for "why this answer" (pure).
 * @param {ReturnType<typeof normalizeQueryResponse>} normalized
 * @param {{ locked: boolean, inWorkspace: boolean, formWorkId: string }} ctx
 * @returns {string[]}
 */
export function buildAskAnswerRationale(normalized, ctx) {
  const locked = Boolean(ctx?.locked);
  const inWorkspace = Boolean(ctx?.inWorkspace);
  const formWid = ctx?.formWorkId != null ? String(ctx.formWorkId).trim() : "";
  const rt = normalized?.retrieval_trace;
  const gc = normalized?.graph_context;
  const citations = Array.isArray(normalized?.citations) ? normalized.citations.length : 0;
  const hits = rt && Number.isFinite(Number(rt.hit_count)) ? Number(rt.hit_count) : 0;
  const tk = rt && Number.isFinite(Number(rt.top_k_requested)) ? Number(rt.top_k_requested) : 0;

  const bullets = [];
  if (locked || inWorkspace) {
    bullets.push(
      "Query mode: workspace session — the answer stays tied to the active work so citations and follow-up tools share the same traceability path.",
    );
  } else if (formWid) {
    bullets.push(
      "Query mode: paper-scoped — retrieval prefers chunks linked to the work_id you entered (you can still open other papers from citations).",
    );
  } else {
    bullets.push(
      "Query mode: corpus-wide — evidence may come from any indexed work that matches the vector query, not a single paper.",
    );
  }

  bullets.push(
    `Evidence pack: ${citations} citation(s) in the answer UI, requested top_k=${tk}, retriever reported ${hits} raw hit(s).`,
  );

  const rtDeg = Array.isArray(rt?.degraded) ? rt.degraded.length : 0;
  const gcDeg = Array.isArray(gc?.degraded) ? gc.degraded.length : 0;
  if (rtDeg + gcDeg > 0) {
    bullets.push(
      "Quality: retrieval or graph context reported degraded steps — use the info alert and retrieval trace (advanced JSON if needed) before treating the answer as definitive.",
    );
  } else {
    bullets.push("Quality: no degraded flags were reported for retrieval or graph context on this response.");
  }

  if (gc) {
    if (gc.semantic_available) {
      bullets.push("Graph context: semantic signals were available; methods/datasets chips reflect structured graph hints when present.");
    } else if (gc.error) {
      bullets.push(`Graph context: limited — ${gc.error}.`);
    } else {
      bullets.push("Graph context: semantic graph signals were not available; the answer still uses vector citations.");
    }
  }

  return bullets.slice(0, 5);
}

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
      retrieval_policy: rt.retrieval_policy == null ? null : String(rt.retrieval_policy),
      filter_work_id: rt.filter_work_id == null ? null : String(rt.filter_work_id),
      resolved_work_id: rt.resolved_work_id == null ? null : String(rt.resolved_work_id),
      qdrant_collection: rt.qdrant_collection == null ? "" : String(rt.qdrant_collection),
      top_k_requested: Number.isFinite(Number(rt.top_k_requested)) ? Number(rt.top_k_requested) : 0,
      citations_returned: Number.isFinite(Number(rt.citations_returned)) ? Number(rt.citations_returned) : 0,
      degraded: Array.isArray(rt.degraded) ? rt.degraded.map(String) : [],
    },
  };
}

/** GET /health (same origin as API when `VITE_API_BASE_URL` is set). */
export async function getHealth(config) {
  const base = getResearchApiBaseUrl();
  const path = "/health";
  const url = base ? `${base}${path}` : path;
  return axios.get(url, config);
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
