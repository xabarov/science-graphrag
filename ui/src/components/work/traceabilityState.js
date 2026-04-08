import { normalizeWorkspaceTab } from "../../pages/WorkspacePage/utils/workContext.js";

export const TRACEABILITY_QUERY_KEYS = {
  workId: "work_id",
  tab: "tab",
  nodeId: "node",
  chunkFingerprint: "chunk_fingerprint",
  section: "section",
  citation: "citation",
};

function trimOrEmpty(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @returns {{workId: string, tab: string, nodeId: string, chunkFingerprint: string, section: string, citation: string}}
 */
export function readTraceabilityState(searchParams) {
  return {
    workId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.workId)),
    tab: normalizeWorkspaceTab(searchParams.get(TRACEABILITY_QUERY_KEYS.tab) || "overview"),
    nodeId: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.nodeId)),
    chunkFingerprint: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.chunkFingerprint)),
    section: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.section)),
    citation: trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.citation)),
  };
}

/**
 * @param {Partial<{workId: string, tab: string, nodeId: string, chunkFingerprint: string, section: string, citation: string}>} state
 * @param {{ includeTab?: boolean }} [options]
 * @returns {URLSearchParams}
 */
export function buildTraceabilityParams(state = {}, options = {}) {
  const includeTab = options.includeTab !== false;
  const params = new URLSearchParams();
  const workId = trimOrEmpty(state.workId);
  const tab = normalizeWorkspaceTab(state.tab || "overview");
  const nodeId = trimOrEmpty(state.nodeId);
  const chunkFingerprint = trimOrEmpty(state.chunkFingerprint);
  const section = trimOrEmpty(state.section);
  const citation = trimOrEmpty(state.citation);

  if (workId) params.set(TRACEABILITY_QUERY_KEYS.workId, workId);
  if (includeTab && workId) params.set(TRACEABILITY_QUERY_KEYS.tab, tab);
  if (nodeId) params.set(TRACEABILITY_QUERY_KEYS.nodeId, nodeId);
  if (chunkFingerprint) params.set(TRACEABILITY_QUERY_KEYS.chunkFingerprint, chunkFingerprint);
  if (section) params.set(TRACEABILITY_QUERY_KEYS.section, section);
  if (citation) params.set(TRACEABILITY_QUERY_KEYS.citation, citation);
  return params;
}

/**
 * @param {string} workId
 * @param {string} tab
 * @param {Partial<{nodeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
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
 * @param {Partial<{nodeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildStandaloneTracePath(routePath, workId, extras = {}) {
  const params = buildTraceabilityParams({ workId, ...extras }, { includeTab: false });
  const query = params.toString();
  return query ? `${routePath}?${query}` : routePath;
}

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @param {Partial<{workId: string, tab: string, nodeId: string, chunkFingerprint: string, section: string, citation: string}>} updates
 * @param {{ includeTab?: boolean }} [options]
 * @returns {URLSearchParams}
 */
export function mergeTraceabilityParams(searchParams, updates = {}, options = {}) {
  const current = readTraceabilityState(searchParams);
  return buildTraceabilityParams({ ...current, ...updates }, options);
}

/**
 * @param {{ nodeId?: string, chunkFingerprint?: string, section?: string, citation?: string }} state
 * @returns {Array<string>}
 */
export function describeTraceabilityState(state = {}) {
  const parts = [];
  const nodeId = trimOrEmpty(state.nodeId);
  const chunkFingerprint = trimOrEmpty(state.chunkFingerprint);
  const section = trimOrEmpty(state.section);
  const citation = trimOrEmpty(state.citation);
  if (citation) parts.push(`citation #${citation}`);
  if (chunkFingerprint) parts.push(`chunk ${chunkFingerprint}`);
  if (section) parts.push(`section ${section}`);
  if (nodeId) parts.push(`node ${nodeId}`);
  return parts;
}
