/** Active work context: URL + localStorage restore for workspace-first navigation. */

export const LAST_WORK_ID_KEY = "science-graphrag:lastWorkId";

export const WORKSPACE_TAB_SLUGS = ["overview", "reader", "graph", "ask", "evidence"];

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
 * @param {string} [tab]
 * @returns {string}
 */
export function buildWorkspacePath(workId, tab = "overview") {
  const t = normalizeWorkspaceTab(tab);
  if (!workId || !String(workId).trim()) {
    return "/workspace";
  }
  const params = new URLSearchParams();
  params.set("work_id", String(workId).trim());
  params.set("tab", t);
  return `/workspace?${params.toString()}`;
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
