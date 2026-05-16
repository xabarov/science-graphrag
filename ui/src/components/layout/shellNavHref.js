/**
 * Shell drawer / cross-route links: preserve traceability query (ask_session, work_id, …).
 */
import { buildInflightChatHref } from "../work/ask/session/askRunPersistence.js";
import { CHAT_PATH, GRAPH_PATH, READER_PATH } from "../../routes/paths.js";
import { TRACEABILITY_QUERY_KEYS } from "../../routing/queryKeys.js";
import {
  mergeTraceabilityParams,
  readTraceabilityState,
} from "../work/traceability/traceabilityState.js";

export const LAST_CHAT_HREF_STORAGE_KEY = "science-graphrag:lastChatHref:v1";

function safeSessionStorage() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

/**
 * Remember last chat deep link (for return from Settings / admin routes).
 * @param {string} href e.g. `/chat?workspace_id=…&ask_session=…`
 */
export function persistLastChatHref(href) {
  const storage = safeSessionStorage();
  const h = String(href || "").trim();
  if (!storage || !h.startsWith(CHAT_PATH)) return;
  try {
    storage.setItem(LAST_CHAT_HREF_STORAGE_KEY, h);
  } catch {
    /* ignore quota */
  }
}

/** @returns {string} */
export function readLastChatHref() {
  const storage = safeSessionStorage();
  if (!storage) return "";
  try {
    return String(storage.getItem(LAST_CHAT_HREF_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

/**
 * Build a tool route href, merging current location query with workspace scope.
 *
 * @param {string} pathname e.g. `/chat`, `/graph`, `/reader`
 * @param {{ locationSearch?: string, workspaceId?: string }} opts
 * @returns {string}
 */
export function buildShellToolHref(pathname, { locationSearch = "", workspaceId = "" } = {}) {
  const path = String(pathname || "").trim();
  const wid = String(workspaceId || "").trim();
  const sp = mergeTraceabilityParams(
    new URLSearchParams(locationSearch || ""),
    { workspaceId: wid || undefined },
    { includeTab: false },
  );
  const qs = sp.toString();
  return qs ? `${path}?${qs}` : path;
}

/**
 * True when the current location carries trace params worth preserving on tool switch.
 * @param {string} locationSearch
 */
export function locationHasPreservableTrace(locationSearch = "") {
  const trace = readTraceabilityState(new URLSearchParams(locationSearch || ""));
  return Boolean(
    trace.workId ||
      trace.nodeId ||
      trace.edgeId ||
      trace.askSession ||
      trace.chunkFingerprint ||
      trace.section ||
      trace.citation,
  );
}

/**
 * Chat link for drawer: prefer current ask_session; else last persisted chat href.
 *
 * @param {{ locationSearch?: string, workspaceId?: string }} opts
 * @returns {string}
 */
export function resolveDrawerChatHref({ locationSearch = "", workspaceId = "" } = {}) {
  const current = new URLSearchParams(locationSearch || "");
  if (current.get(TRACEABILITY_QUERY_KEYS.askSession) || locationHasPreservableTrace(locationSearch)) {
    return buildShellToolHref(CHAT_PATH, { locationSearch, workspaceId });
  }
  const inflight = buildInflightChatHref(workspaceId);
  if (inflight.startsWith(CHAT_PATH)) {
    return inflight;
  }
  const last = readLastChatHref();
  if (last.startsWith(CHAT_PATH)) {
    return last;
  }
  return buildShellToolHref(CHAT_PATH, { locationSearch, workspaceId });
}

/** @param {string} pathname */
export function isShellToolPath(pathname) {
  const p = String(pathname || "").split("?")[0];
  return p === CHAT_PATH || p === GRAPH_PATH || p === READER_PATH;
}
