import { normalizeWorkspaceTab } from "../../pages/WorkspacePage/utils/workContext.js";
import { CHAT_PATH } from "../../routes/paths.js";

/** Dispatched after {@link replaceHashTraceabilitySelection} so HashRouter consumers re-read the hash. */
export const TRACEABILITY_HASH_SELECTION_EVENT = "science-graphrag:traceability-hash-selection";

export const TRACEABILITY_QUERY_KEYS = {
  workId: "work_id",
  workspaceId: "workspace_id",
  tab: "tab",
  nodeId: "node",
  /** Normalized graph edge id (Canvas selection); mutual exclusion with `node` for deep links. */
  edgeId: "edge",
  chunkFingerprint: "chunk_fingerprint",
  section: "section",
  citation: "citation",
  /** Local Ask session id (browser-only; preserved across workspace links when present). */
  askSession: "ask_session",
};

function trimOrEmpty(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @returns {{workId: string, workspaceId: string, tab: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string, askSession: string}}
 */
/**
 * Read graph selection (`node`, `edge`) from the current `window.location.hash` query.
 * Used when selection is updated via `history.replaceState` (React Router may lag).
 *
 * @returns {{ nodeId: string, edgeId: string, hashHasQuery: boolean }}
 */
export function readTraceabilityGraphSelectionFromHash() {
  if (typeof window === "undefined") {
    return { nodeId: "", edgeId: "", hashHasQuery: false };
  }
  const hash = window.location.hash || "#/";
  const queryAt = hash.indexOf("?");
  if (queryAt < 0) {
    return { nodeId: "", edgeId: "", hashHasQuery: false };
  }
  const params = new URLSearchParams(hash.slice(queryAt + 1));
  return {
    nodeId: trimOrEmpty(params.get(TRACEABILITY_QUERY_KEYS.nodeId)),
    edgeId: trimOrEmpty(params.get(TRACEABILITY_QUERY_KEYS.edgeId)),
    hashHasQuery: true,
  };
}

/**
 * Prefer hash query for graph `node` / `edge` when the hash carries a query string
 * (selection updated via replaceState).
 *
 * @param {ReturnType<typeof readTraceabilityState>} routerState
 * @param {{ nodeId: string, edgeId: string, hashHasQuery: boolean }} hashSelection
 */
export function mergeTraceabilityStateWithHashSelection(routerState, hashSelection) {
  if (!hashSelection.hashHasQuery) return routerState;
  return { ...routerState, nodeId: hashSelection.nodeId, edgeId: hashSelection.edgeId };
}

export function readTraceabilityState(searchParams) {
  return {
    workId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.workId)),
    workspaceId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.workspaceId)),
    tab: normalizeWorkspaceTab(searchParams.get(TRACEABILITY_QUERY_KEYS.tab) || "overview"),
    nodeId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.nodeId)),
    edgeId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.edgeId)),
    chunkFingerprint: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.chunkFingerprint)),
    section: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.section)),
    citation: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.citation)),
    askSession: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.askSession)),
  };
}

/**
 * @param {Partial<{workId: string, workspaceId: string, tab: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string, askSession: string}>} state
 * @param {{ includeTab?: boolean }} [options]
 * @returns {URLSearchParams}
 */
export function buildTraceabilityParams(state = {}, options = {}) {
  const includeTab = options.includeTab !== false;
  const params = new URLSearchParams();
  const workId = trimOrEmpty(state.workId);
  const workspaceId = trimOrEmpty(state.workspaceId);
  const tab = normalizeWorkspaceTab(state.tab || "overview");
  const nodeId = trimOrEmpty(state.nodeId);
  const edgeId = trimOrEmpty(state.edgeId);
  const chunkFingerprint = trimOrEmpty(state.chunkFingerprint);
  const section = trimOrEmpty(state.section);
  const citation = trimOrEmpty(state.citation);
  const askSession = trimOrEmpty(state.askSession);

  if (workId) params.set(TRACEABILITY_QUERY_KEYS.workId, workId);
  if (workspaceId) params.set(TRACEABILITY_QUERY_KEYS.workspaceId, workspaceId);
  if (includeTab && workId) params.set(TRACEABILITY_QUERY_KEYS.tab, tab);
  if (nodeId) params.set(TRACEABILITY_QUERY_KEYS.nodeId, nodeId);
  if (edgeId) params.set(TRACEABILITY_QUERY_KEYS.edgeId, edgeId);
  if (chunkFingerprint) params.set(TRACEABILITY_QUERY_KEYS.chunkFingerprint, chunkFingerprint);
  if (section) params.set(TRACEABILITY_QUERY_KEYS.section, section);
  if (citation) params.set(TRACEABILITY_QUERY_KEYS.citation, citation);
  if (askSession) params.set(TRACEABILITY_QUERY_KEYS.askSession, askSession);
  return params;
}

/**
 * @param {string} workId
 * @param {string} tab
 * @param {Partial<{nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildWorkspaceTracePath(workId, tab, extras = {}) {
  const wid = trimOrEmpty(workId);
  if (!wid) return "/workspace";
  const params = buildTraceabilityParams({ workId: wid, tab, ...extras });
  return `/workspace?${params.toString()}`;
}

/**
 * @param {string} routePath
 * @param {string} workId
 * @param {Partial<{nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildStandaloneTracePath(routePath, workId, extras = {}) {
  const params = buildTraceabilityParams({ workId, ...extras }, { includeTab: false });
  const query = params.toString();
  return query ? `${routePath}?${query}` : routePath;
}

/**
 * Canonical URL for chunk-level evidence inspection (standalone `/evidence`).
 * Prefer this over {@link buildWorkspaceTracePath} with `tab: "evidence"` because the workspace
 * shell is a paper list; tools (Reader, Graph, Chat, Evidence) live as top-level routes.
 *
 * @param {string} workId
 * @param {Partial<{workspaceId: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildStandaloneEvidencePath(workId, extras = {}) {
  return buildStandaloneTracePath("/evidence", workId, extras);
}

/**
 * Standalone chat deep link with optional trace extras (chunk/section/citation/workspace).
 *
 * @param {string} workId
 * @param {Partial<{workspaceId: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string, askSession: string}>} [extras]
 * @returns {string}
 */
export function buildStandaloneChatPath(workId, extras = {}) {
  return buildStandaloneTracePath(CHAT_PATH, workId, extras);
}

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @param {Partial<{workId: string, workspaceId: string, tab: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string, askSession: string}>} updates
 * @param {{ includeTab?: boolean }} [options]
 * @returns {URLSearchParams}
 */
export function mergeTraceabilityParams(searchParams, updates = {}, options = {}) {
  const current = readTraceabilityState(searchParams);
  return buildTraceabilityParams({ ...current, ...updates }, options);
}

/**
 * Update only graph selection params in the current hash URL without notifying React Router.
 *
 * Canvas selection is high-frequency UI state. Pushing it through `setSearchParams`
 * turns every click into route navigation and can remount/rebuild graph views.
 *
 * @param {Partial<{nodeId: string, edgeId: string}>} updates
 */
export function replaceHashTraceabilitySelection(updates = {}) {
  if (typeof window === "undefined") return;
  const hash = window.location.hash || "#/";
  const queryAt = hash.indexOf("?");
  const routeHash = queryAt >= 0 ? hash.slice(0, queryAt) : hash;
  const params = new URLSearchParams(queryAt >= 0 ? hash.slice(queryAt + 1) : "");
  if (Object.prototype.hasOwnProperty.call(updates, "nodeId")) {
    const nodeId = trimOrEmpty(updates.nodeId);
    if (nodeId) params.set(TRACEABILITY_QUERY_KEYS.nodeId, nodeId);
    else params.delete(TRACEABILITY_QUERY_KEYS.nodeId);
  }
  if (Object.prototype.hasOwnProperty.call(updates, "edgeId")) {
    const edgeId = trimOrEmpty(updates.edgeId);
    if (edgeId) params.set(TRACEABILITY_QUERY_KEYS.edgeId, edgeId);
    else params.delete(TRACEABILITY_QUERY_KEYS.edgeId);
  }
  const qs = params.toString();
  const nextHash = `${routeHash || "#/"}${qs ? `?${qs}` : ""}`;
  window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}${nextHash}`);
  try {
    window.dispatchEvent(new CustomEvent(TRACEABILITY_HASH_SELECTION_EVENT));
  } catch {
    /* ignore */
  }
}

/**
 * @param {{ nodeId?: string, edgeId?: string, chunkFingerprint?: string, section?: string, citation?: string }} state
 * @returns {Array<string>}
 */
export function describeTraceabilityState(state = {}) {
  const parts = [];
  const nodeId = trimOrEmpty(state.nodeId);
  const edgeId = trimOrEmpty(state.edgeId);
  const chunkFingerprint = trimOrEmpty(state.chunkFingerprint);
  const section = trimOrEmpty(state.section);
  const citation = trimOrEmpty(state.citation);
  if (citation) parts.push(`citation #${citation}`);
  if (chunkFingerprint) parts.push(`chunk ${chunkFingerprint}`);
  if (section) parts.push(`section ${section}`);
  if (edgeId) parts.push(`edge ${edgeId}`);
  if (nodeId) parts.push(`node ${nodeId}`);
  return parts;
}
