import { WORKSPACE_SHELL_QUERY_KEYS } from "../../../routing/queryKeys.js";
import { WORKSPACE_PATH } from "../../../routes/paths.js";

/**
 * Active work context: URL + localStorage restore for workspace-first navigation.
 *
 * ## Routing contract: `/workspace`
 *
 * - `workspace_id` — Neo4j workspace collection (required for server-backed list).
 * - `work_id` — optional focus within that workspace.
 * - **Selected work** (UI focus + `persistWorkId`) is resolved by {@link resolveSelectedWorkId}:
 *   if `work_id` is present and belongs to `workspace.work_ids`, use it; else if exactly one
 *   paper in the workspace, use it; else use the first paper in list order (Neo4j `collect` order);
 *   if the list is empty, none.
 * - Callers that open a specific paper must set both query params via {@link buildWorkspacePath}.
 *
 * ## Tabs vs standalone tools
 *
 * - **Canonical:** the workspace shell is a paper list (`overview`-equivalent); Reader, Graph, Chat,
 *   Evidence are top-level routes (`/reader`, `/graph`, `/chat`, `/evidence`).
 * - **Legacy:** `tab=reader|graph|ask` in `/workspace` URLs is still recognized by
 *   {@link normalizeWorkspaceTab} and traceability parsing for bookmarks; the app redirects to
 *   standalone routes (see `legacyWorkspaceTabRedirectTarget` in `traceabilityState.js`).
 */

export const LAST_WORK_ID_KEY = "science-graphrag:lastWorkId";

/**
 * Slugs accepted in legacy `tab=` query values and localStorage-shaped payloads.
 * Only `overview` is meaningful for the workspace shell; `reader` / `graph` / `ask` are legacy
 * tool tabs mapped to standalone routes elsewhere.
 */
export const WORKSPACE_TAB_SLUGS = ["overview", "reader", "graph", "ask"];

/**
 * @param {string} tab
 * @returns {string}
 */
export function normalizeWorkspaceTab(tab) {
  const t = (tab || "overview").toLowerCase();
  return WORKSPACE_TAB_SLUGS.includes(t) ? t : "overview";
}

/**
 * @param {string | null | undefined} workId
 * @param {string} [tab] legacy; ignored — workspace is a paper list, tools live in the left nav.
 * @param {{ workspaceId?: string | null }} [options]
 * @returns {string}
 */
export function buildWorkspacePath(workId, tab = "overview", options = {}) {
  void tab;
  const wid = workId && String(workId).trim() ? String(workId).trim() : "";
  const ws = options?.workspaceId != null && String(options.workspaceId).trim() ? String(options.workspaceId).trim() : "";
  if (!wid && !ws) {
    return WORKSPACE_PATH;
  }
  const params = new URLSearchParams();
  if (wid) params.set(WORKSPACE_SHELL_QUERY_KEYS.workId, wid);
  if (ws) params.set(WORKSPACE_SHELL_QUERY_KEYS.workspaceId, ws);
  return `${WORKSPACE_PATH}?${params.toString()}`;
}

/**
 * Resolve which `work_id` should be treated as the focused paper for a workspace.
 *
 * @param {{ workIds: string[], workIdFromUrl?: string | null }} args
 * @returns {string} empty string when there is no selection
 */
export function resolveSelectedWorkId({ workIds, workIdFromUrl }) {
  const ids = Array.isArray(workIds) ? workIds.map((x) => String(x || "").trim()).filter(Boolean) : [];
  if (!ids.length) return "";
  const fromUrl = workIdFromUrl != null ? String(workIdFromUrl).trim() : "";
  if (fromUrl && ids.includes(fromUrl)) return fromUrl;
  if (ids.length === 1) return ids[0];
  return ids[0];
}

/**
 * @param {string} workId
 */
export function persistWorkId(workId) {
  const id = String(workId || "").trim();
  if (!id) return;
  try {
    window.localStorage.setItem(LAST_WORK_ID_KEY, id);
  } catch {
    // ignore
  }
}

/**
 * @returns {string}
 */
export function getLastWorkId() {
  try {
    const raw = window.localStorage.getItem(LAST_WORK_ID_KEY);
    return raw && String(raw).trim() ? String(raw).trim() : "";
  } catch {
    return "";
  }
}
