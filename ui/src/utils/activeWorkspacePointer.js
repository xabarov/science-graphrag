/**
 * Synchronous active-workspace pointer in localStorage (no HTTP / researchApi).
 * Kept separate from workspaceStore.js so early imports (e.g. HomePage/homeState) avoid
 * pulling the full workspace API module graph, which can break named exports under cycles.
 */

const ACTIVE_WORKSPACE_KEY = "science-graphrag:activeWorkspaceId";

/**
 * @returns {string}
 */
export function getActiveWorkspaceId() {
  try {
    const raw = window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
    return raw && String(raw).trim() ? String(raw).trim() : "";
  } catch {
    return "";
  }
}

/**
 * @param {string} id
 */
export function setActiveWorkspaceId(id) {
  const v = String(id || "").trim();
  try {
    if (!v) window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
    else window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, v);
  } catch {
    /* ignore */
  }
}
