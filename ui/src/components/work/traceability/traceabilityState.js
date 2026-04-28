/**
 * Traceability URL state (read / build / merge / standalone paths).
 * HTTP query key names: `TRACEABILITY_QUERY_KEYS` in `ui/src/routing/queryKeys.js` (re-exported from `routing/index.js`).
 */
import { normalizeWorkspaceTab } from "../../../pages/WorkspacePage/utils/workContext.js";
import { TRACEABILITY_QUERY_KEYS } from "../../../routing/queryKeys.js";
import {
  CHAT_PATH,
  EVIDENCE_PATH,
  GRAPH_PATH,
  READER_PATH,
  WORKSPACE_PATH,
} from "../../../routes/paths.js";

function trimOrEmpty(value) {
  if (value == null) return "";
  return String(value).trim();
}

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @returns {{workId: string, workspaceId: string, tab: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string, askSession: string}}
 */
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
 * Legacy `/workspace?...&tab=...` URL builder. The workspace shell is a paper list; reader/graph/chat
 * are standalone routes — use {@link buildStandaloneTracePath} or {@link buildStandaloneChatPath} for new links.
 *
 * @deprecated Prefer standalone tool paths; kept for tests and rare compatibility.
 * @param {string} workId
 * @param {string} tab
 * @param {Partial<{nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildWorkspaceTracePath(workId, tab, extras = {}) {
  const wid = trimOrEmpty(workId);
  if (!wid) return WORKSPACE_PATH;
  const params = buildTraceabilityParams({ workId: wid, tab, ...extras });
  return `${WORKSPACE_PATH}?${params.toString()}`;
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
 * Canonical URL for chunk-level evidence inspection (standalone evidence route).
 * Prefer this over {@link buildWorkspaceTracePath} with `tab: "evidence"` because the workspace
 * shell is a paper list; tools (Reader, Graph, Chat, Evidence) live as top-level routes.
 *
 * @param {string} workId
 * @param {Partial<{workspaceId: string, nodeId: string, edgeId: string, chunkFingerprint: string, section: string, citation: string}>} [extras]
 * @returns {string}
 */
export function buildStandaloneEvidencePath(workId, extras = {}) {
  return buildStandaloneTracePath(EVIDENCE_PATH, workId, extras);
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

const LEGACY_REDIRECT_TOOL_TABS = new Set(["reader", "graph", "ask"]);

/**
 * When `/workspace` has legacy `tab=reader|graph|ask`, returns the canonical standalone path for `replace` navigation.
 *
 * @param {URLSearchParams | { get: (key: string) => string | null }} searchParams
 * @returns {string | null}
 */
export function legacyWorkspaceTabRedirectTarget(searchParams) {
  const rawTab = trimOrEmpty(searchParams.get(TRACEABILITY_QUERY_KEYS.tab)).toLowerCase();
  if (!LEGACY_REDIRECT_TOOL_TABS.has(rawTab)) return null;
  const trace = readTraceabilityState(searchParams);
  const extras = {
    workspaceId: trace.workspaceId,
    nodeId: trace.nodeId,
    edgeId: trace.edgeId,
    chunkFingerprint: trace.chunkFingerprint,
    section: trace.section,
    citation: trace.citation,
    askSession: trace.askSession,
  };
  const workId = trace.workId;
  if (rawTab === "ask") return buildStandaloneChatPath(workId, extras);
  if (rawTab === "reader") return buildStandaloneTracePath(READER_PATH, workId, extras);
  return buildStandaloneTracePath(GRAPH_PATH, workId, extras);
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
