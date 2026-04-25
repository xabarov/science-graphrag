import { apiClient, buildApiUrl, getApiBaseUrl } from "./apiClient.js";

/**
 * Base URL for the research API (no trailing slash). Empty string = same-origin `/v1/*`
 * (Vite dev proxy + FastAPI static deploy).
 */
export function getResearchApiBaseUrl() {
  return getApiBaseUrl();
}

/**
 * Human-readable message from a failed research API call (axios or generic Error).
 * Matches FastAPI-style `detail` when present.
 * @param {unknown} err
 * @returns {string}
 */
export function formatResearchApiError(err) {
  const raw = err?.response?.data?.detail;
  if (raw !== undefined && raw !== null) {
    return typeof raw === "string" ? raw : JSON.stringify(raw);
  }
  if (err != null && typeof err === "object" && "message" in err && typeof err.message === "string") {
    return err.message;
  }
  return String(err);
}

export function buildQueryBody(query, workId = null, topK = 5, workspaceId = null, mode = "vector") {
  const t = Math.trunc(Number(topK));
  const tk = Number.isFinite(t) ? Math.min(24, Math.max(1, t)) : 5;
  const wid = workId === undefined || workId === "" ? null : workId;
  const ws =
    workspaceId === undefined || workspaceId === null || workspaceId === ""
      ? null
      : String(workspaceId).trim() || null;
  const modeRaw = String(mode || "vector").toLowerCase();
  const m = modeRaw === "hybrid" ? "hybrid" : modeRaw === "agent" ? "agent" : "vector";
  return {
    query: String(query ?? "").trim(),
    work_id: wid,
    workspace_id: ws,
    top_k: tk,
    mode: m,
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
  if (rt.retrieval_mode) {
    lines.push(`Mode: ${String(rt.retrieval_mode)}`);
  }
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
  return apiClient.get(buildApiUrl("/health"), config);
}

export async function postQuery(body, config) {
  return apiClient.post(buildApiUrl("/v1/query"), body, config);
}

export async function postAgentQuery(body, config) {
  return apiClient.post(buildApiUrl("/v1/agent/query"), body, config);
}

export async function postIdeaAssist(body, config) {
  return apiClient.post(buildApiUrl("/v1/agent/idea-assist"), body, config);
}

function worksUrl(pathWithQuery) {
  return buildApiUrl(pathWithQuery);
}

/** GET /v1/works */
export async function getWorks({
  q,
  limit = 20,
  offset = 0,
  yearMin,
  yearMax,
  hasSemantic,
} = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (q != null && String(q).trim() !== "") params.set("q", String(q).trim());
  if (yearMin != null && Number.isFinite(Number(yearMin))) params.set("year_min", String(yearMin));
  if (yearMax != null && Number.isFinite(Number(yearMax))) params.set("year_max", String(yearMax));
  if (hasSemantic === true) params.set("has_semantic", "true");
  if (hasSemantic === false) params.set("has_semantic", "false");
  return apiClient.get(worksUrl(`/v1/works?${params.toString()}`));
}

/** GET/PATCH/DELETE /v1/ask-sessions — server-backed Ask history (optional UI integration). */
export async function listAskSessions(scope) {
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.get(worksUrl(`/v1/ask-sessions?scope=${s}`));
}

export async function createAskSession(scope, { title } = {}) {
  return apiClient.post(worksUrl("/v1/ask-sessions"), { scope, title });
}

export async function patchAskSession(scope, sessionId, body) {
  const sid = encodeURIComponent(String(sessionId ?? "").trim());
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.patch(worksUrl(`/v1/ask-sessions/${sid}?scope=${s}`), body);
}

export async function deleteAskSession(scope, sessionId) {
  const sid = encodeURIComponent(String(sessionId ?? "").trim());
  const s = encodeURIComponent(String(scope ?? "").trim());
  return apiClient.delete(worksUrl(`/v1/ask-sessions/${sid}?scope=${s}`));
}

/** Absolute URL for GET /v1/works/{work_id}/pdf (for react-pdf ``file`` prop). */
export function workPdfUrl(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return worksUrl(`/v1/works/${id}/pdf`);
}

/** GET /v1/works/{work_id}/sources */
export async function getWorkSources(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(worksUrl(`/v1/works/${id}/sources`));
}

/** GET /v1/works/{work_id} */
export async function getWorkDetail(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(worksUrl(`/v1/works/${id}`));
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
  return apiClient.get(worksUrl(`/v1/works/${id}/chunks?${params.toString()}`));
}

/** GET /v1/works/{work_id}/claims */
export async function getWorkClaims(workId) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  return apiClient.get(worksUrl(`/v1/works/${id}/claims`));
}

/**
 * GET /v1/works/{work_id}/graph
 * @param {string} workId
 * @param {{ neighborLimit?: number, depth?: number }} [options]
 */
export async function getWorkGraph(workId, options = {}) {
  const id = encodeURIComponent(String(workId ?? "").trim());
  const params = new URLSearchParams();
  if (options.neighborLimit != null && Number.isFinite(Number(options.neighborLimit))) {
    const lim = Math.min(2000, Math.max(1, Math.floor(Number(options.neighborLimit))));
    params.set("neighbor_limit", String(lim));
  }
  if (options.depth != null && Number.isFinite(Number(options.depth))) {
    const d = Math.min(3, Math.max(1, Math.floor(Number(options.depth))));
    params.set("depth", String(d));
  }
  if (options.prioritize != null && String(options.prioritize).trim()) {
    params.set("prioritize", String(options.prioritize).trim());
  }
  const q = params.toString();
  return apiClient.get(worksUrl(`/v1/works/${id}/graph${q ? `?${q}` : ""}`));
}
